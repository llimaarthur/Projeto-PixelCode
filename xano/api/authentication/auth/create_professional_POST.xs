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

    db.query user {
      where = $db.user.email == $input.email
      return = {type: "single"}
    } as $existing_user

    precondition ($existing_user == null) {
      error_type = "inputerror"
      error = "A professional with this email already exists."
    }

    security.create_uuid as $temporary_secret

    var $temporary_password {
      value = "TmpA1-" ~ $temporary_secret
    }

    var $normalized_phone {
      value = $input.phone|regex_replace:"[^0-9]":""
    }

    var $normalized_cpf {
      value = $input.cpf|regex_replace:"[^0-9]":""
    }

    precondition (($normalized_phone|strlen) == 10 || ($normalized_phone|strlen) == 11) {
      error_type = "inputerror"
      error = "Informe um telefone com DDD e 10 ou 11 dígitos."
    }

    db.query user {
      where = $db.user.cpf == $normalized_cpf
      return = {type: "single"}
    } as $existing_cpf

    precondition ($existing_cpf == null) {
      error_type = "inputerror"
      error = "Já existe um cadastro com este CPF."
    }

    db.query contact {
      where = $db.contact.cpf_normalized == $normalized_cpf
      return = {type: "list"}
    } as $existing_contact_cpf

    precondition (($existing_contact_cpf|count) == 0) {
      error_type = "inputerror"
      error = "Já existe um cadastro com este CPF."
    }

    db.add user {
      data = {
        created_at            : "now"
        name                  : $input.name
        email                 : $input.email
        phone                 : $normalized_phone
        cpf                   : $normalized_cpf
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
  guid = "vYCLiKiI8JmILjzep2Zgz6FC3cw"
}