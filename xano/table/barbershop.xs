table barbershop {
  auth = false

  schema {
    int id
    timestamp created_at?=now
    text name filters=trim
    enum status?=active {
      values = ["active", "inactive"]
    }
    text migration_key?
    bool migration_completed?=false
    bool legacy_compatibility?=false
    json weekly_hours?
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "migration_key", op: "asc"}]}
    {type: "btree", field: [{name: "status", op: "asc"}]}
  ]
  guid = "smx9WDgttdajJKvOaL4Z0Zbp7oA"
}
