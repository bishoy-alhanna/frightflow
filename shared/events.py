"""
Kafka event producer/consumer wrappers for event-driven architecture.
"""
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, asdict
import threading
import time

try:
    from kafka import KafkaProducer, KafkaConsumer
    from kafka.errors import KafkaError
except ImportError:
    KafkaProducer = None
    KafkaConsumer = None
    KafkaError = Exception

from flask import current_app, g

logger = logging.getLogger(__name__)


@dataclass
class Event:
    """Base event structure."""
    event_type: str
    event_id: str
    timestamp: str
    correlation_id: str
    source_service: str
    data: Dict[str, Any]
    version: str = "1.0"
    
    @classmethod
    def create(cls, event_type: str, data: Dict[str, Any], source_service: str,
               correlation_id: Optional[str] = None) -> 'Event':
        """Create a new event instance."""
        return cls(
            event_type=event_type,
            event_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow().isoformat(),
            correlation_id=correlation_id or getattr(g, 'correlation_id', str(uuid.uuid4())),
            source_service=source_service,
            data=data
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert event to JSON string."""
        return json.dumps(self.to_dict(), default=str)


class EventProducer:
    """Kafka event producer with retry logic and idempotency."""
    
    def __init__(self, bootstrap_servers: Optional[str] = None):
        self.bootstrap_servers = bootstrap_servers
        self._producer = None
        self._lock = threading.Lock()
    
    @property
    def producer(self) -> Optional[KafkaProducer]:
        """Get Kafka producer instance with lazy initialization."""
        if KafkaProducer is None:
            logger.error("Kafka client not available. Install with: pip install kafka-python")
            return None
        
        if self._producer is None:
            with self._lock:
                if self._producer is None:
                    bootstrap_servers = (
                        self.bootstrap_servers or 
                        current_app.config.get('KAFKA_BROKERS', 'localhost:9092')
                    )
                    
                    try:
                        self._producer = KafkaProducer(
                            bootstrap_servers=bootstrap_servers.split(','),
                            value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
                            key_serializer=lambda k: k.encode('utf-8') if k else None,
                            acks='all',  # Wait for all replicas
                            retries=3,
                            retry_backoff_ms=1000,
                            request_timeout_ms=30000,
                            enable_idempotence=True,  # Prevent duplicate messages
                            max_in_flight_requests_per_connection=1
                        )
                        logger.info("Kafka producer initialized successfully")
                    except Exception as e:
                        logger.error(f"Failed to initialize Kafka producer: {e}")
                        return None
        
        return self._producer
    
    def publish(self, topic: str, event: Event, key: Optional[str] = None) -> bool:
        """Publish event to Kafka topic."""
        if not self.producer:
            logger.error("Kafka producer not available")
            return False
        
        try:
            # Use event_id as key if no key provided for partitioning
            message_key = key or event.event_id
            
            # Add headers for tracing
            headers = [
                ('event_type', event.event_type.encode('utf-8')),
                ('correlation_id', event.correlation_id.encode('utf-8')),
                ('source_service', event.source_service.encode('utf-8')),
                ('event_id', event.event_id.encode('utf-8'))
            ]
            
            future = self.producer.send(
                topic=topic,
                value=event.to_dict(),
                key=message_key,
                headers=headers
            )
            
            # Wait for confirmation (blocking)
            record_metadata = future.get(timeout=10)
            
            logger.info(
                f"Published event {event.event_type} to topic {topic} "
                f"(partition: {record_metadata.partition}, offset: {record_metadata.offset})"
            )
            return True
        
        except KafkaError as e:
            logger.error(f"Failed to publish event {event.event_type} to topic {topic}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error publishing event: {e}")
            return False
    
    def publish_batch(self, topic: str, events: List[Event]) -> int:
        """Publish multiple events to Kafka topic."""
        if not self.producer:
            return 0
        
        successful = 0
        for event in events:
            if self.publish(topic, event):
                successful += 1
        
        return successful
    
    def flush(self, timeout: Optional[float] = None):
        """Flush pending messages."""
        if self.producer:
            self.producer.flush(timeout)
    
    def close(self):
        """Close the producer."""
        if self._producer:
            self._producer.close()
            self._producer = None


class EventConsumer:
    """Kafka event consumer with automatic offset management."""
    
    def __init__(self, group_id: str, topics: List[str], bootstrap_servers: Optional[str] = None):
        self.group_id = group_id
        self.topics = topics
        self.bootstrap_servers = bootstrap_servers
        self._consumer = None
        self._handlers: Dict[str, Callable[[Event], bool]] = {}
        self._running = False
        self._thread = None
    
    @property
    def consumer(self) -> Optional[KafkaConsumer]:
        """Get Kafka consumer instance."""
        if KafkaConsumer is None:
            logger.error("Kafka client not available. Install with: pip install kafka-python")
            return None
        
        if self._consumer is None:
            bootstrap_servers = (
                self.bootstrap_servers or 
                current_app.config.get('KAFKA_BROKERS', 'localhost:9092')
            )
            
            try:
                self._consumer = KafkaConsumer(
                    *self.topics,
                    bootstrap_servers=bootstrap_servers.split(','),
                    group_id=self.group_id,
                    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                    key_deserializer=lambda k: k.decode('utf-8') if k else None,
                    auto_offset_reset='earliest',
                    enable_auto_commit=False,  # Manual commit for better control
                    max_poll_records=10,
                    session_timeout_ms=30000,
                    heartbeat_interval_ms=10000
                )
                logger.info(f"Kafka consumer initialized for group {self.group_id}")
            except Exception as e:
                logger.error(f"Failed to initialize Kafka consumer: {e}")
                return None
        
        return self._consumer
    
    def register_handler(self, event_type: str, handler: Callable[[Event], bool]):
        """Register event handler for specific event type."""
        self._handlers[event_type] = handler
        logger.info(f"Registered handler for event type: {event_type}")
    
    def _process_message(self, message) -> bool:
        """Process a single Kafka message."""
        try:
            # Extract event data
            event_data = message.value
            
            # Create Event object
            event = Event(
                event_type=event_data['event_type'],
                event_id=event_data['event_id'],
                timestamp=event_data['timestamp'],
                correlation_id=event_data['correlation_id'],
                source_service=event_data['source_service'],
                data=event_data['data'],
                version=event_data.get('version', '1.0')
            )
            
            # Find and execute handler
            handler = self._handlers.get(event.event_type)
            if handler:
                logger.info(f"Processing event {event.event_type} (ID: {event.event_id})")
                return handler(event)
            else:
                logger.warning(f"No handler registered for event type: {event.event_type}")
                return True  # Consider unhandled events as successfully processed
        
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return False
    
    def _consume_loop(self):
        """Main consumer loop."""
        logger.info(f"Starting consumer loop for topics: {self.topics}")
        
        while self._running:
            try:
                if not self.consumer:
                    time.sleep(5)
                    continue
                
                # Poll for messages
                message_batch = self.consumer.poll(timeout_ms=1000)
                
                for topic_partition, messages in message_batch.items():
                    for message in messages:
                        success = self._process_message(message)
                        
                        if success:
                            # Commit offset for successful processing
                            self.consumer.commit_async({topic_partition: message.offset + 1})
                        else:
                            logger.error(f"Failed to process message at offset {message.offset}")
                            # TODO: Implement dead letter queue logic
            
            except Exception as e:
                logger.error(f"Error in consumer loop: {e}")
                time.sleep(5)
        
        logger.info("Consumer loop stopped")
    
    def start(self):
        """Start consuming messages in background thread."""
        if self._running:
            logger.warning("Consumer is already running")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._consume_loop, daemon=True)
        self._thread.start()
        logger.info("Event consumer started")
    
    def stop(self):
        """Stop consuming messages."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=10)
        
        if self._consumer:
            self._consumer.close()
            self._consumer = None
        
        logger.info("Event consumer stopped")


# Global instances
producer = EventProducer()


def init_events(app):
    """Initialize event system with Flask app."""
    producer.bootstrap_servers = app.config.get('KAFKA_BROKERS')
    logger.info("Event system initialized")


def publish_event(topic: str, event_type: str, data: Dict[str, Any], 
                 source_service: str, key: Optional[str] = None) -> bool:
    """Convenience function to publish an event."""
    event = Event.create(event_type, data, source_service)
    return producer.publish(topic, event, key)


# Predefined event types and topics
class EventTypes:
    """Predefined event types."""
    QUOTE_ISSUED = "quote.issued"
    QUOTE_ACCEPTED = "quote.accepted"
    SHIPMENT_UPDATED = "shipment.updated"
    DOCUMENT_ATTACHED = "document.attached"
    NOTIFY_REQUESTED = "notify.requested"


class Topics:
    """Predefined Kafka topics."""
    QUOTATIONS = "quotations"
    SHIPMENTS = "shipments"
    DOCUMENTS = "documents"
    NOTIFICATIONS = "notifications"


def create_consumer(group_id: str, topics: List[str]) -> EventConsumer:
    """Create a new event consumer."""
    return EventConsumer(group_id, topics)

