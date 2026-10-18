query "services/{service_id}/status" verb=PATCH {
  api_group = "Services"
  auth = "user"

  input {
    int service_id
    enum status {
      values = ["active", "inactive"]
    }
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "admin"}
    } as $role_check

    db.get service {
      field_name = "id"
      field_value = $input.service_id
    } as $existing_service

    precondition ($existing_service != null) {
      error_type = "inputerror"
      error = "Serviço não encontrado."
    }

    db.edit service {
      field_name = "id"
      field_value = $input.service_id
      data = {
        updated_at: "now"
        status    : $input.status
      }
    } as $service
  }

  response = $service
}
