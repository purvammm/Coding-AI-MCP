import asyncio
import json
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from collections import deque
import hashlib

try:
    import tiktoken
    from sentence_transformers import SentenceTransformer
    import numpy as np
except ImportError as e:
    print(f"Warning: Context management libraries not available: {e}")
    print("Install with: pip install tiktoken sentence-transformers numpy")

from models.base import ChatMessage
from .attachment_manager import AttachmentContext

@dataclass
class ConversationTurn:
    id: str
    user_message: ChatMessage
    assistant_message: ChatMessage
    timestamp: datetime
    tokens_used: int
    importance_score: float = 0.0
    summary: Optional[str] = None
    code_blocks: List[str] = None
    attachments: List[str] = None  # attachment IDs

@dataclass
class ContextWindow:
    messages: List[ChatMessage]
    total_tokens: int
    summary: Optional[str] = None
    key_points: List[str] = None

@dataclass
class ConversationSummary:
    period_start: datetime
    period_end: datetime
    summary_text: str
    key_topics: List[str]
    important_code: List[str]
    decisions_made: List[str]
    tokens_saved: int

class ContextManager:
    """Manages conversation context and handles long conversation threads"""
    
    def __init__(self, max_context_tokens: int = 8000):
        self.max_context_tokens = max_context_tokens
        self.conversation_turns: deque = deque(maxlen=1000)  # Keep last 1000 turns
        self.summaries: List[ConversationSummary] = []
        
        # Initialize tokenizer and embedding model
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")  # GPT-4 tokenizer
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        except:
            self.tokenizer = None
            self.embedding_model = None
            print("Warning: Advanced context management features disabled")
        
        # Context management settings
        self.summary_threshold = 20  # Summarize after 20 turns
        self.importance_decay = 0.95  # Decay factor for older messages
        self.code_weight = 1.5  # Weight for messages containing code
        self.attachment_weight = 1.3  # Weight for messages with attachments
    
    def add_conversation_turn(
        self, 
        user_message: ChatMessage, 
        assistant_message: ChatMessage,
        attachment_ids: List[str] = None
    ) -> str:
        """Add a new conversation turn"""
        
        turn_id = self._generate_turn_id(user_message, assistant_message)
        
        # Calculate tokens
        tokens_used = self._count_tokens([user_message, assistant_message])
        
        # Extract code blocks
        code_blocks = self._extract_code_blocks(assistant_message.content)
        
        # Calculate importance score
        importance_score = self._calculate_importance_score(
            user_message, assistant_message, code_blocks, attachment_ids
        )
        
        turn = ConversationTurn(
            id=turn_id,
            user_message=user_message,
            assistant_message=assistant_message,
            timestamp=datetime.now(),
            tokens_used=tokens_used,
            importance_score=importance_score,
            code_blocks=code_blocks,
            attachments=attachment_ids or []
        )
        
        self.conversation_turns.append(turn)
        
        # Check if we need to summarize
        if len(self.conversation_turns) >= self.summary_threshold:
            asyncio.create_task(self._maybe_create_summary())
        
        return turn_id
    
    async def get_context_window(
        self, 
        current_message: str,
        attachment_contexts: List[AttachmentContext] = None
    ) -> ContextWindow:
        """Get optimized context window for current conversation"""
        
        if not self.conversation_turns:
            return ContextWindow(messages=[], total_tokens=0)
        
        # Start with recent messages
        selected_messages = []
        total_tokens = 0
        
        # Add system message space
        system_tokens = 500  # Reserve for system message
        available_tokens = self.max_context_tokens - system_tokens
        
        # Add current message tokens
        current_tokens = self._count_tokens([ChatMessage("user", current_message)])
        available_tokens -= current_tokens
        
        # Add attachment context tokens
        attachment_tokens = 0
        if attachment_contexts:
            for ctx in attachment_contexts:
                attachment_tokens += len(ctx.summary.split()) * 1.3  # Rough token estimate
        available_tokens -= attachment_tokens
        
        # Select messages using smart strategy
        selected_turns = await self._select_relevant_turns(
            current_message, available_tokens
        )
        
        # Convert turns to messages
        for turn in selected_turns:
            selected_messages.extend([turn.user_message, turn.assistant_message])
            total_tokens += turn.tokens_used
        
        # Add summaries if we have them
        summary_text = await self._get_relevant_summary(current_message)
        
        # Create key points
        key_points = self._extract_key_points(selected_turns)
        
        return ContextWindow(
            messages=selected_messages,
            total_tokens=total_tokens + system_tokens + current_tokens + attachment_tokens,
            summary=summary_text,
            key_points=key_points
        )
    
    async def _select_relevant_turns(
        self, 
        current_message: str, 
        available_tokens: int
    ) -> List[ConversationTurn]:
        """Select most relevant conversation turns for context"""
        
        if not self.conversation_turns:
            return []
        
        # Calculate relevance scores for all turns
        turn_scores = []
        
        for i, turn in enumerate(reversed(self.conversation_turns)):
            # Base score from importance
            score = turn.importance_score
            
            # Recency bonus (more recent = higher score)
            recency_factor = (self.importance_decay ** i)
            score *= recency_factor
            
            # Semantic similarity bonus
            if self.embedding_model:
                similarity = self._calculate_semantic_similarity(
                    current_message, 
                    turn.user_message.content + " " + turn.assistant_message.content
                )
                score += similarity * 0.5
            
            # Keyword matching bonus
            keyword_score = self._calculate_keyword_similarity(
                current_message, 
                turn.user_message.content + " " + turn.assistant_message.content
            )
            score += keyword_score * 0.3
            
            turn_scores.append((turn, score))
        
        # Sort by score
        turn_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Select turns that fit in token budget
        selected_turns = []
        used_tokens = 0
        
        for turn, score in turn_scores:
            if used_tokens + turn.tokens_used <= available_tokens:
                selected_turns.append(turn)
                used_tokens += turn.tokens_used
            else:
                break
        
        # Sort selected turns by timestamp to maintain conversation flow
        selected_turns.sort(key=lambda x: x.timestamp)
        
        return selected_turns
    
    def _calculate_importance_score(
        self, 
        user_message: ChatMessage, 
        assistant_message: ChatMessage,
        code_blocks: List[str],
        attachment_ids: List[str]
    ) -> float:
        """Calculate importance score for a conversation turn"""
        
        base_score = 1.0
        
        # Code presence bonus
        if code_blocks:
            base_score *= self.code_weight
        
        # Attachment bonus
        if attachment_ids:
            base_score *= self.attachment_weight
        
        # Length bonus (longer responses often more important)
        response_length = len(assistant_message.content)
        if response_length > 500:
            base_score *= 1.2
        elif response_length > 1000:
            base_score *= 1.4
        
        # Question complexity bonus
        user_content = user_message.content.lower()
        complexity_keywords = [
            'implement', 'create', 'build', 'design', 'architecture',
            'debug', 'fix', 'error', 'problem', 'issue',
            'explain', 'how', 'why', 'what', 'when'
        ]
        
        complexity_score = sum(1 for keyword in complexity_keywords if keyword in user_content)
        base_score += complexity_score * 0.1
        
        return min(base_score, 3.0)  # Cap at 3.0
    
    def _calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity between two texts"""
        if not self.embedding_model:
            return 0.0
        
        try:
            embeddings = self.embedding_model.encode([text1, text2])
            similarity = np.dot(embeddings[0], embeddings[1]) / (
                np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
            )
            return float(similarity)
        except:
            return 0.0
    
    def _calculate_keyword_similarity(self, text1: str, text2: str) -> float:
        """Calculate keyword-based similarity"""
        
        # Extract keywords (simple approach)
        def extract_keywords(text):
            # Remove common words and extract meaningful terms
            words = re.findall(r'\b\w+\b', text.lower())
            stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those'}
            return set(word for word in words if len(word) > 2 and word not in stop_words)
        
        keywords1 = extract_keywords(text1)
        keywords2 = extract_keywords(text2)
        
        if not keywords1 or not keywords2:
            return 0.0
        
        intersection = keywords1.intersection(keywords2)
        union = keywords1.union(keywords2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _extract_code_blocks(self, content: str) -> List[str]:
        """Extract code blocks from message content"""
        # Match code blocks (```...```)
        code_pattern = r'```[\s\S]*?```'
        code_blocks = re.findall(code_pattern, content)
        
        # Also match inline code (`...`)
        inline_pattern = r'`[^`]+`'
        inline_code = re.findall(inline_pattern, content)
        
        return code_blocks + inline_code
    
    def _extract_key_points(self, turns: List[ConversationTurn]) -> List[str]:
        """Extract key points from selected conversation turns"""
        key_points = []
        
        for turn in turns:
            # Extract important sentences from assistant responses
            sentences = turn.assistant_message.content.split('.')
            
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) > 20:  # Ignore very short sentences
                    # Check for key indicators
                    if any(indicator in sentence.lower() for indicator in [
                        'important', 'note', 'remember', 'key', 'main',
                        'solution', 'answer', 'result', 'conclusion'
                    ]):
                        key_points.append(sentence)
            
            # Add code blocks as key points
            if turn.code_blocks:
                for code in turn.code_blocks:
                    if len(code) < 200:  # Only short code snippets
                        key_points.append(f"Code: {code}")
        
        return key_points[:10]  # Limit to 10 key points
    
    async def _get_relevant_summary(self, current_message: str) -> Optional[str]:
        """Get relevant summary from previous conversation periods"""
        if not self.summaries:
            return None
        
        # Find most relevant summary
        best_summary = None
        best_score = 0.0
        
        for summary in self.summaries:
            score = 0.0
            
            # Check topic relevance
            for topic in summary.key_topics:
                if topic.lower() in current_message.lower():
                    score += 1.0
            
            # Check keyword similarity
            keyword_score = self._calculate_keyword_similarity(
                current_message, summary.summary_text
            )
            score += keyword_score
            
            if score > best_score:
                best_score = score
                best_summary = summary
        
        return best_summary.summary_text if best_summary and best_score > 0.5 else None
    
    async def _maybe_create_summary(self):
        """Create summary if needed"""
        if len(self.conversation_turns) < self.summary_threshold:
            return
        
        # Take older turns for summarization
        turns_to_summarize = list(self.conversation_turns)[:self.summary_threshold // 2]
        
        if not turns_to_summarize:
            return
        
        summary = await self._create_conversation_summary(turns_to_summarize)
        if summary:
            self.summaries.append(summary)
            
            # Remove summarized turns to save memory
            for _ in range(len(turns_to_summarize)):
                if self.conversation_turns:
                    self.conversation_turns.popleft()
    
    async def _create_conversation_summary(
        self, 
        turns: List[ConversationTurn]
    ) -> Optional[ConversationSummary]:
        """Create a summary of conversation turns"""
        
        if not turns:
            return None
        
        # Extract key information
        all_text = []
        code_blocks = []
        topics = set()
        decisions = []
        
        for turn in turns:
            all_text.append(turn.user_message.content)
            all_text.append(turn.assistant_message.content)
            
            if turn.code_blocks:
                code_blocks.extend(turn.code_blocks)
            
            # Extract topics (simple keyword extraction)
            content = turn.user_message.content + " " + turn.assistant_message.content
            words = re.findall(r'\b\w+\b', content.lower())
            
            # Look for technical terms
            tech_terms = [word for word in words if len(word) > 4 and 
                         any(char.isupper() for char in word) or
                         word in ['python', 'javascript', 'react', 'api', 'database', 'function', 'class', 'method']]
            topics.update(tech_terms[:5])  # Limit topics
            
            # Look for decisions/conclusions
            if any(indicator in turn.assistant_message.content.lower() for indicator in [
                'solution', 'approach', 'recommend', 'suggest', 'should', 'will'
            ]):
                decisions.append(turn.assistant_message.content[:200] + "...")
        
        # Create summary text (simplified)
        combined_text = " ".join(all_text)
        summary_text = self._create_simple_summary(combined_text)
        
        # Calculate tokens saved
        original_tokens = sum(turn.tokens_used for turn in turns)
        summary_tokens = len(summary_text.split()) * 1.3  # Rough estimate
        tokens_saved = int(original_tokens - summary_tokens)
        
        return ConversationSummary(
            period_start=turns[0].timestamp,
            period_end=turns[-1].timestamp,
            summary_text=summary_text,
            key_topics=list(topics)[:10],
            important_code=code_blocks[:5],
            decisions_made=decisions[:3],
            tokens_saved=tokens_saved
        )
    
    def _create_simple_summary(self, text: str) -> str:
        """Create a simple extractive summary"""
        sentences = text.split('.')
        
        # Score sentences by importance
        sentence_scores = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 20:
                continue
            
            score = 0
            
            # Length bonus
            score += min(len(sentence) / 100, 1.0)
            
            # Keyword bonus
            important_words = ['implement', 'create', 'solution', 'problem', 'error', 'fix', 'code', 'function', 'class', 'method', 'api', 'database']
            for word in important_words:
                if word in sentence.lower():
                    score += 1
            
            sentence_scores.append((sentence, score))
        
        # Select top sentences
        sentence_scores.sort(key=lambda x: x[1], reverse=True)
        top_sentences = [s[0] for s in sentence_scores[:5]]
        
        return '. '.join(top_sentences) + '.'
    
    def _count_tokens(self, messages: List[ChatMessage]) -> int:
        """Count tokens in messages"""
        if not self.tokenizer:
            # Rough estimate: 1 token ≈ 0.75 words
            total_text = " ".join(msg.content for msg in messages)
            return int(len(total_text.split()) * 1.33)
        
        try:
            total_text = " ".join(msg.content for msg in messages)
            return len(self.tokenizer.encode(total_text))
        except:
            # Fallback to word count
            total_text = " ".join(msg.content for msg in messages)
            return int(len(total_text.split()) * 1.33)
    
    def _generate_turn_id(self, user_msg: ChatMessage, assistant_msg: ChatMessage) -> str:
        """Generate unique ID for conversation turn"""
        content = user_msg.content + assistant_msg.content + str(datetime.now())
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def get_conversation_stats(self) -> Dict[str, Any]:
        """Get conversation statistics"""
        if not self.conversation_turns:
            return {}
        
        total_turns = len(self.conversation_turns)
        total_tokens = sum(turn.tokens_used for turn in self.conversation_turns)
        avg_importance = sum(turn.importance_score for turn in self.conversation_turns) / total_turns
        
        code_turns = sum(1 for turn in self.conversation_turns if turn.code_blocks)
        attachment_turns = sum(1 for turn in self.conversation_turns if turn.attachments)
        
        return {
            'total_turns': total_turns,
            'total_tokens': total_tokens,
            'average_importance': round(avg_importance, 2),
            'turns_with_code': code_turns,
            'turns_with_attachments': attachment_turns,
            'summaries_created': len(self.summaries),
            'tokens_saved_by_summaries': sum(s.tokens_saved for s in self.summaries)
        }
