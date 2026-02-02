# Usage - TMS Route Optimizer Distance Cache

## Overview

The distance cache works automatically behind the scenes. Once installed, no user action is
required to benefit from improved performance.

## How It Works

### Automatic Caching

When you run a route optimization:

1. **First Run**: Distances are calculated and stored in cache
2. **Subsequent Runs**: Cached distances are reused for matching coordinates
3. **Cache Updates**: Last used timestamp updated on every access
4. **Automatic Cleanup**: Old unused entries removed when limit is reached

### Cache Key

The cache uses normalized coordinates as keys:

- **Rounding**: Coordinates rounded to 6 decimal places (~0.1 meter precision)
- **Ordering**: Points ordered consistently (smaller coordinates first)
- **Symmetry**: Distance A→B same as B→A (stored once)

Example:

```
Point A: (lat=23.550520, lon=-46.633308)
Point B: (lat=23.547745, lon=-46.636023)

Cache Key: (23.547745, -46.636023, 23.550520, -46.633308)
```

## Performance Benefits

### Scenario: Daily Route Optimization

**Without Cache**:

- 50 stops × 50 stops = 2,500 distance calculations
- Each calculation ~0.1ms
- Total time: ~250ms per optimization

**With Cache** (after first run):

- 2,500 cache lookups
- Each lookup ~0.01ms
- Total time: ~25ms (10× faster)

### Real-World Example

**Company with recurring delivery locations**:

- 100 stops per day
- 80% location overlap daily
- First optimization: 100% cache misses
- Subsequent optimizations: 80% cache hits
- Performance improvement: 5-8× faster

## Monitoring Cache Performance

### View Cache Entries

1. Go to **Settings > Technical**
2. Enable Developer Mode
3. Navigate to **Database Structure > Models**
4. Search for `tms.route.distance.cache`
5. Click **Records** to view all cached distances

### Cache Entry Information

Each entry shows:

- **Lat A / Lon A**: First coordinate pair
- **Lat B / Lon B**: Second coordinate pair
- **Distance (km)**: Cached distance value
- **Last Used**: Timestamp of most recent access

### Analyze Cache Usage

To see which routes are most cached:

```python
# Get top 10 most recently used cache entries
cache = env['tms.route.distance.cache']
top_entries = cache.sudo().search([], order='last_used desc', limit=10)

for entry in top_entries:
    print(f"Distance: {entry.distance_km:.2f} km, Last used: {entry.last_used}")
```

## Manual Operations

### Clear Entire Cache

If you need to clear all cached distances:

```python
env['tms.route.distance.cache'].sudo().search([]).unlink()
```

**Use Cases**:

- Changing distance calculation method
- Migrating to different geolocation data
- Testing optimization performance

### Force Cache Cleanup

To manually trigger LRU cleanup:

```python
env['tms.route.distance.cache'].cron_cleanup_distance_cache()
```

This removes oldest entries if cache exceeds configured limit.

### Check Cache Size

```python
cache_model = env['tms.route.distance.cache']
count = cache_model.sudo().search_count([])
limit = cache_model._get_cache_limit()

print(f"Cache entries: {count} / {limit}")
print(f"Usage: {(count/limit*100):.1f}%" if limit > 0 else "Unlimited")
```

## Best Practices

### Optimize Cache Size

1. **Monitor** cache size over 1-2 weeks of normal operations
2. **Adjust** limit parameter to cover typical distance pairs
3. **Balance** between memory usage and hit rate

### Recurring Routes

For maximum benefit:

- Keep delivery locations consistent when possible
- Group orders by geographic area
- Run optimizations at similar times daily

### Cache Warm-up

Before peak operations:

1. Run optimization with representative stops
2. Cache populates with common distances
3. Subsequent optimizations benefit immediately

### Maintenance Schedule

- **Daily**: Automatic cleanup via scheduled action
- **Weekly**: Review cache size and adjust limit if needed
- **Monthly**: Analyze cache hit patterns
- **As Needed**: Clear cache if geolocation data changes

## Troubleshooting

### "Distance cache entry already exists" Error

This indicates a database constraint violation (should not happen in normal use).

**Solution**: Check for corrupted data or duplicate entries

```python
# Find potential duplicates
env.cr.execute("""
    SELECT lat_a, lon_a, lat_b, lon_b, COUNT(*)
    FROM tms_route_distance_cache
    GROUP BY lat_a, lon_a, lat_b, lon_b
    HAVING COUNT(*) > 1
""")
duplicates = env.cr.fetchall()
```

### Cache Not Reducing Optimization Time

**Possible Causes**:

1. **First Run**: Cache needs to be populated first
2. **Different Locations**: Stops have no overlapping coordinates
3. **High Precision**: Coordinates vary beyond 6 decimal places

**Solutions**:

- Run multiple optimizations with same/similar stops
- Verify coordinates are consistent across runs
- Check that location data is stable

### Cache Growing Unbounded

1. Verify scheduled action is active
2. Check cache limit parameter is set correctly
3. Manually run cleanup if needed

```python
# Check scheduled action status
cron = env.ref('tms_route_optimizer_distance_cache.ir_cron_tms_route_distance_cache_cleanup')
print(f"Active: {cron.active}, Interval: {cron.interval_number} {cron.interval_type}")
```

## Integration Tips

### API / External Integration

When calling optimization via API:

```python
# The cache works automatically
optimizer = env['tms.route.optimizer'].create({
    'name': 'API Optimization',
    'team_id': team.id,
    # ... other fields
})
optimizer.run_optimization()  # Uses cache automatically
```

### Custom Distance Providers

If implementing custom distance calculation:

```python
# Use cache in custom calculations
cache = env['tms.route.distance.cache']
distance = cache.get_distance(lat1, lon1, lat2, lon2)
# Returns cached value or calculates and stores new distance
```
