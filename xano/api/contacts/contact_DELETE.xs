query "contacts/{contact_id}" verb=DELETE {
  api_group = "Contacts"
  auth = "user"

  input {
    int contact_id
  }

  stack {
    precondition (false) {
      error_type = "accessdenied"
      error = "Contatos não podem ser excluídos permanentemente."
    }
  }

  response = null
  guid = "OeCwHZr3wU3m8g1kP2JYPiFUqA8"
}
