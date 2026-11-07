// Allows an administrator to restore a professional account's CPF and password.
query "auth/professionals/repair" verb=POST {
  api_group = "Authentication"
  auth = "user"

  input {
    email account_email filters=trim|lower
    text professional_cpf filters=trim
    password replacement_password filters=min:8|minAlpha:1|minDigit:1
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "admin"}
    } as $role_check

    db.get user {
      field_name = "email"
      field_value = $input.account_email
      output = ["id", "name", "email", "role", "status"]
    } as $professional

    precondition ($professional != null && $professional.role == "professional") {
      error_type = "inputerror"
      error = "A professional account with this email was not found."
    }

    var $normalized_cpf {
      value = $input.professional_cpf|regex_replace:"[^0-9]":""
    }

    precondition (($normalized_cpf|strlen) == 11) {
      error_type = "inputerror"
      error = "Informe os 11 dígitos do CPF correto."
    }

    db.query user {
      where = $db.user.cpf == $normalized_cpf && $db.user.id != $professional.id
      return = {type: "list"}
    } as $existing_user_cpf

    precondition (($existing_user_cpf|count) == 0) {
      error_type = "inputerror"
      error = "Este CPF já está associado a outra conta."
    }

    db.query contact {
      where = $db.contact.cpf_normalized == $normalized_cpf
      return = {type: "list"}
    } as $existing_contact_cpf

    precondition (($existing_contact_cpf|count) == 0) {
      error_type = "inputerror"
      error = "Este CPF já está associado a um cadastro de cliente."
    }

    db.edit user {
      field_name = "id"
      field_value = $professional.id
      data = {
        cpf                  : $normalized_cpf
        password             : $input.replacement_password
        must_change_password : false
      }
    } as $updated_professional

    function.run "Quick Start/log_event" {
      input = {
        user_id : $auth.id
        action  : "professional_access_repaired"
        metadata: {professional_id: $updated_professional.id}
      }
    } as $event_log
  }

  response = {
    success: true
    email  : $updated_professional.email
  }
  guid = "pR0f3ss10n4lsRpr20261107"
}
