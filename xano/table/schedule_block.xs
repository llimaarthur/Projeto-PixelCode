table schedule_block {
  auth = false

  schema {
    int id
    timestamp created_at?=now
    timestamp updated_at?=now
    int professional_id? {
      table = "user"
    }
    timestamp start_at
    timestamp end_at
    text reason? filters=trim
    enum status?=active {
      values = ["active", "released"]
    }
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "professional_id", op: "asc"}, {name: "start_at", op: "asc"}]}
    {type: "btree", field: [{name: "status", op: "asc"}]}
  ]
  guid = "jK6mQ8vY2nR5pT9wX1aC3dF7hL0"
}
