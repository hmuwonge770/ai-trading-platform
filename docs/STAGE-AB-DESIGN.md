# Stage AB design

The alert delivery component is deliberately small: immutable alert data, an injected sink, bounded deduplication, and explicit delivery status. It contains no exchange integration.
