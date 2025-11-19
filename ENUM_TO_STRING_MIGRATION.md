# Enum to String Migration

## What Changed

Converted the `source_type` column in the `review_sources` table from a PostgreSQL ENUM to a simple VARCHAR(50) column.

## Why

- **Flexibility**: Adding new source types no longer requires database migrations
- **Simplicity**: No more enum management headaches
- **Compatibility**: Easier to work with across different database systems
- **No Transaction Issues**: Enums in PostgreSQL require special handling outside transactions

## Migration Details

### Before
```sql
source_type sourcetypeenum NOT NULL
-- Where sourcetypeenum was: ('REDDIT', 'TWITTER', 'CUSTOM_CSV', 'CUSTOM_JSON')
```

### After
```sql
source_type VARCHAR(50) NOT NULL
-- Can be any string: 'reddit', 'twitter', 'g2', 'trustpilot', etc.
```

### Python Code
The `SourceTypeEnum` class still exists in Python for type safety and IDE autocomplete, but it's not enforced at the database level:

```python
class SourceTypeEnum(str, enum.Enum):
    """Available review source types (for Python code only, not DB constraint)."""
    REDDIT = "reddit"
    TWITTER = "twitter"
    G2 = "g2"
    TRUSTPILOT = "trustpilot"
    CUSTOM_CSV = "custom_csv"
    CUSTOM_JSON = "custom_json"
```

## Migration Applied

Migration `019_convert_enum_to_string.py` was successfully applied:

1. ✅ Added temporary string column
2. ✅ Copied data from enum to string (lowercase)
3. ✅ Dropped old enum column and indexes
4. ✅ Renamed new column to `source_type`
5. ✅ Recreated indexes
6. ✅ Dropped enum type from database

## Seeded Data

Successfully seeded 6 review sources:

### Real Sources (4)
- ✅ Reddit
- ✅ Twitter/X
- ✅ G2
- ✅ Trustpilot

### Fake Sources (2)
- ✅ LLM Fake Reviews - Reddit
- ✅ LLM Fake Reviews - Twitter/X

## Benefits

1. **Easy to Add New Sources**: Just insert a new row, no migration needed
2. **No Enum Sync Issues**: No need to keep Python enum and DB enum in sync
3. **Cleaner Migrations**: No more complex enum alteration logic
4. **Better Portability**: Works the same across PostgreSQL, MySQL, SQLite, etc.

## Backward Compatibility

- ✅ All existing code continues to work
- ✅ Python enum still provides type safety
- ✅ API responses unchanged
- ✅ Frontend unchanged

## Testing

Run the application and verify:
```bash
# Backend
cd backend
./scripts/start.sh

# Frontend
cd frontend
npm run dev
```

Navigate to Data Sources page and verify all 6 sources appear correctly grouped by real/fake.

## Future

Adding new source types is now trivial:
```python
# Just add to Python enum (optional, for type safety)
class SourceTypeEnum(str, enum.Enum):
    # ... existing ...
    YELP = "yelp"  # New!

# And seed it
{
    "name": "Yelp",
    "source_type": SourceTypeEnum.YELP,  # or just "yelp"
    "description": "Scrape reviews from Yelp",
    # ...
}
```

No database migration required! 🎉

