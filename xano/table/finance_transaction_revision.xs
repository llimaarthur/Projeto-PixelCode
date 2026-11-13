table finance_transaction_revision {
  auth = false

  schema {
    int id
    timestamp changed_at?=now
    enum action {
      values = ["edited", "cancelled"]
    }
    int transaction_id {
      table = "finance_transaction"
    }
    int changed_by {
      table = "user"
    }
    enum previous_type {
      values = ["income", "expense"]
    }
    decimal previous_amount
    text previous_title
    text previous_detail? filters=trim
    timestamp previous_occurred_at
    text reason? filters=trim
    int previous_contact_id? {
      table = "contact"
    }
    text previous_contact_name_snapshot? filters=trim
    json previous_services_snapshot?
    int previous_appointment_id? {
      table = "appointment"
    }
    enum previous_appointment_status? {
      values = ["pending", "confirmed"]
    }
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "transaction_id", op: "asc"}, {name: "changed_at", op: "desc"}]}
    {type: "btree", field: [{name: "changed_by", op: "asc"}]}
  ]
  guid = "dS5X8fPmK2wL7aNq4rT6vB"
}
