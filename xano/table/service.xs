table service {
  auth = false

  schema {
    int id
    timestamp created_at?=now
    timestamp updated_at?=now
    text name filters=trim
    text description? filters=trim
    decimal price
    int duration_minutes

    enum status?=active {
      values = ["active", "inactive"]
    }
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "status", op: "asc"}]}
    {type: "btree", field: [{name: "name", op: "asc"}]}
  ]
}
