// No destructive ops. Establish minimal shape and ready MERGE semantics.
// Optionally, create stub nodes to warm caches (optional, usually skipped).
MERGE (warmup:User {id: '__warmup__'}) DELETE warmup