table service {
  auth = false

  schema {
    int id
    timestamp created_at?=now
    timestamp updated_at?=now
    int barbershop_id? {
      table = "barbershop"
    }
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
    {type: "btree", field: [{name: "barbershop_id", op: "asc"}]}
    {type: "btree", field: [{name: "status", op: "asc"}]}
    {type: "btree", field: [{name: "name", op: "asc"}]}
  ]
  guid = "a-Ix-QInd464L_CP9nFriZwtt-A"
}
