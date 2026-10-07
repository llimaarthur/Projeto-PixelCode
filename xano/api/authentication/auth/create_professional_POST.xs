// Creates a professional account with a temporary password. Only the administrator may call this endpoint.
query "auth/professionals" verb=POST {
  api_group = "Authentication"
  auth = "user"

  input {
    text name filters=trim
    email email filters=trim|lower
    text phone filters=trim
    text cpf filters=trim
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "admin"}
    } as $role_check

    precondition ($input.name != "" && $input.email != "" && $input.phone != "" && $input.cpf != "") {
      error_type = "inputerror"
      error = "Name, email, phone, and CPF are required."
    }

    db.get user {
      field_name = "email"
      field_value = $input.email
      output = ["id"]
    } as $existing_user

    precondition ($existing_user == null) {
      error_type = "inputerror"
      error = "A professional with this email already exists."
    }

    db.get user {
      field_name = "role"
      field_value = "admin"
      output = ["id"]
    } as $existing_admin

    precondition ($existing_admin != null && $existing_admin.id == $auth.id) {
      error_type = "accessdenied"
      error = "Only the existing administrator can provision professionals."
    }

    security.create_uuid as $temporary_secret

    var $temporary_password {
      value = "TmpA1-" ~ $temporary_secret
    }

    db.add user {
      data = {
        created_at            : "now"
        name                  : $input.name
        email                 : $input.email
        phone                 : $input.phone
        cpf                   : $input.cpf
        password              : $temporary_password
        role                  : "professional"
        status                : "active"
        must_change_password  : true
      }
    } as $professional

    function.run "Quick Start/log_event" {
      input = {
        user_id : $auth.id
        action  : "professional_created"
        metadata: {professional_id: $professional.id}
      }
    } as $event_log
  }

  response = {
    id                   : $professional.id
    name                 : $professional.name
    email                : $professional.email
    role                 : $professional.role
    must_change_password : $professional.must_change_password
    temporary_password   : $temporary_password
  }
}