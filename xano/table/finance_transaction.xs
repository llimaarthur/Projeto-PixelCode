table finance_transaction {
  auth = false

  schema {
    int id
    timestamp created_at?=now
    timestamp updated_at?=now
    enum type {
      values = ["income", "expense"]
    }
    enum status?=active {
      values = ["active", "cancelled"]
    }
    decimal amount
    text title filters=trim
    text detail? filters=trim
    timestamp occurred_at
    int created_by {
      table = "user"
    }
    int contact_id? {
      table = "contact"
    }
    text contact_name_snapshot? filters=trim
    json services_snapshot?
    int appointment_id? {
      table = "appointment"
    }
    enum appointment_status_before_payment? {
      values = ["pending", "confirmed"]
    }
    timestamp cancelled_at?
    int cancelled_by? {
      table = "user"
    }
    text cancellation_reason? filters=trim
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "occurred_at", op: "desc"}]}
    {type: "btree", field: [{name: "type", op: "asc"}, {name: "occurred_at", op: "desc"}]}
    {type: "btree", field: [{name: "created_by", op: "asc"}]}
    {type: "btree", field: [{name: "appointment_id", op: "asc"}, {name: "status", op: "asc"}]}
  ]
  guid = "engF48ZSTB5NLMAUHOBwyhCJozg"
}
