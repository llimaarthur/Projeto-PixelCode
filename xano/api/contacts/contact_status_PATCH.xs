query "contacts/{contact_id}/status" verb=PATCH {
  api_group = "Contacts"
  auth = "user"

  input {
    int contact_id
    enum status {
      values = ["active", "inactive"]
    }
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "professional"}
    } as $role_check

    db.get contact {
      field_name = "id"
      field_value = $input.contact_id
    } as $existing_contact

    precondition ($existing_contact != null) {
      error_type = "inputerror"
      error = "Contato não encontrado."
    }

    db.edit contact {
      field_name = "id"
      field_value = $input.contact_id
      data = {
        updated_at: "now"
        status    : $input.status
      }
    } as $contact
  }

  response = $contact
  guid = "6k1DvI41OWcsWRqZucicZ1f62LQ"
}
