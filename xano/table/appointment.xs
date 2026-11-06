table appointment {
  auth = false

  schema {
    int id
    timestamp created_at?=now
    timestamp updated_at?=now
    int contact_id {
      table = "contact"
    }
    text contact_name_snapshot filters=trim
    text contact_phone_snapshot filters=trim
    int professional_id {
      table = "user"
    }
    text professional_name_snapshot filters=trim
    timestamp start_at
    timestamp end_at
    int duration_minutes
    decimal total_price
    json services_snapshot
    text notes? filters=trim
    enum status?=pending {
      values = ["pending", "confirmed", "completed", "cancelled"]
    }
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "professional_id", op: "asc"}, {name: "start_at", op: "asc"}]}
    {type: "btree", field: [{name: "contact_id", op: "asc"}]}
    {type: "btree", field: [{name: "status", op: "asc"}]}
  ]
  guid = "lEAPmIo3m27K2OjV5uBvaS6hufo"
}
