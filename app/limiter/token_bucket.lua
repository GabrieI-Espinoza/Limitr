-- KEYS[1] = Redis key for this client's token bucket
local key = KEYS[1]

-- ARGV[1] = bucket capacity
local capacity = tonumber(ARGV[1])

-- ARGV[2] = refill rate in tokens per second
local refill_rate_per_sec = tonumber(ARGV[2])

-- Get the current time from Redis 
local time_res = redis.call('TIME')
local current_time = tonumber(time_res[1]) + (tonumber(time_res[2]) / 1000000)

-- Get the current state of the specified users bucket
local bucket = redis.call('HMGET', key, 'tokens_remaining', 'last_refill_timestamp')


local tokens = tonumber(bucket[1])
local last_refill_timestamp = tonumber(bucket[2])

if not tokens or not last_refill_timestamp then
    -- No existing bucket, initialize with full capacity
    tokens = capacity
    -- Set the last refill timestamp to now
    last_refill_timestamp = current_time
else
    -- Calculate how many tokens to add based on the time elapsed since the last refill
    local elapsed_time = math.max(0, current_time - last_refill_timestamp)
    local tokens_to_add = elapsed_time * refill_rate_per_sec

    -- Add the new tokens to the bucket, ensuring capacity is not exceeded
    tokens = math.min(capacity, tokens + tokens_to_add)
    -- Update the last refill timestamp to now
    last_refill_timestamp = current_time
end

local allowed = 0
local retry_after_seconds = 0

-- Check if there are enough tokens to allow the request
if tokens >= 1 then
    -- Consume one token and allow the request
    tokens = tokens - 1
    allowed = 1
else
    -- Not enough tokens, reject the request and calculate retry after time
    local missing_tokens = 1 - tokens
    retry_after_seconds = math.ceil(missing_tokens / refill_rate_per_sec)
end

-- Update the bucket state in Redis
redis.call(
    'HMSET',
    key,
    'tokens_remaining', tokens,
    'last_refill_timestamp', last_refill_timestamp
)

-- Expiration logic in case client is inactive for a long time
local ttl_seconds = math.ceil(capacity / refill_rate_per_sec) + 10
redis.call('EXPIRE', key, ttl_seconds)

return {allowed, tokens, retry_after_seconds}