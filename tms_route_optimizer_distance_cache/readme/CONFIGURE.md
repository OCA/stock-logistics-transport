# Configuration - TMS Route Optimizer Distance Cache

## Module Dependencies

This module requires:

- `tms_route_optimizer`: Base route optimization module

## Installation

No special installation steps required beyond installing the module.

## Configuration

### Cache Size Limit

The cache size is controlled by a system parameter that can be configured in Odoo:

1. Go to **Settings > Technical > Parameters > System Parameters**
2. Find or create parameter: `tms.route_optimizer.distance_cache_limit`
3. Set the value to desired maximum number of cache entries (default: 200000)

**Recommended Values**:

- **Small Operations** (< 50 stops/day): 10,000 entries
- **Medium Operations** (50-200 stops/day): 50,000 entries
- **Large Operations** (> 200 stops/day): 200,000+ entries
- **Set to 0**: Disables cache cleanup (unlimited cache, use with caution)

### Cache Cleanup Schedule

The module includes a scheduled action that runs daily to clean up old cache entries:

1. Go to **Settings > Technical > Automation > Scheduled Actions**
2. Find action: **TMS Route Distance Cache Cleanup**
3. Configure:
   - **Interval Number**: 1 (default)
   - **Interval Unit**: Days (default)
   - **Active**: True

**Note**: The cleanup only removes entries when the total count exceeds the configured
limit, keeping the most recently used entries.

## Integration with tms_route_optimizer

This module integrates automatically with `tms_route_optimizer`. No additional configuration
is needed. The cache is used transparently during route optimization:

1. When optimization calculates distances, it first checks the cache
2. Cache hits return stored distance immediately
3. Cache misses calculate distance and store it for future use
4. Last used timestamp is updated on each access

## Performance Monitoring

To monitor cache performance:

### Check Cache Size

```python
cache_count = env['tms.route.distance.cache'].sudo().search_count([])
print(f"Current cache entries: {cache_count}")
```

### View Cache Statistics

1. Go to **Settings > Technical > Database Structure > Models**
2. Search for: `tms.route.distance.cache`
3. Click **Records** to view cached entries

### Clear Cache Manually

To clear all cache entries:

```python
env['tms.route.distance.cache'].sudo().search([]).unlink()
```

## Storage Considerations

### Database Size

Each cache entry stores:

- 2 coordinate pairs (4 float values)
- 1 distance value (float)
- 1 timestamp (datetime)
- System fields (create_date, write_date, etc.)

**Estimated Storage**: ~200-300 bytes per entry

**Total Storage Examples**:

- 10,000 entries: ~2-3 MB
- 50,000 entries: ~10-15 MB
- 200,000 entries: ~40-60 MB

### Cleanup Impact

The LRU cleanup ensures:

- Cache stays within configured limit
- Most frequently used distances remain cached
- Oldest unused entries are removed first
- No manual intervention needed

## Troubleshooting

### Cache Not Working

1. Verify module is installed: `tms_route_optimizer_distance_cache`
2. Check system parameter exists: `tms.route_optimizer.distance_cache_limit`
3. Ensure cache table exists in database

### Cache Growing Too Large

1. Reduce cache limit parameter
2. Run cleanup manually: `model.cron_cleanup_distance_cache()`
3. Check scheduled action is active and running

### Performance Not Improving

- Cache needs time to populate with frequently used distances
- First optimization is always slower (populates cache)
- Subsequent optimizations with overlapping locations will be faster
- Monitor cache hit rate by checking if entries are being reused
