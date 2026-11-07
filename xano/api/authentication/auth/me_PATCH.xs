// Allows an authenticated professional to update only their own profile.
query "auth/me" verb=PATCH {
  api_group = "Authentication"
  auth = "user"

  input {
    text profile_name filters=trim
    email profile_email filters=trim|lower
    text profile_phone filters=trim
    text profile_cpf? filters=trim
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "professional"}
    } as $role_check

    db.get user {
      field_name = "id"
      field_value = $auth.id
      output = ["id", "cpf"]
    } as $existing_user

    precondition ($input.profile_name != "" && ($input.profile_name|strlen) <= 120) {
      error_type = "inputerror"
      error = "Informe um nome válido de até 120 caracteres."
    }

    precondition ($input.profile_email != "") {
      error_type = "inputerror"
      error = "Informe um e-mail válido."
    }

    var $phone_digits {
      value = $input.profile_phone
    }

    var $cpf_digits {
      value = $existing_user.cpf
    }

    precondition (($phone_digits|strlen) >= 10 && ($phone_digits|strlen) <= 11) {
      error_type = "inputerror"
      error = "Informe um telefone com DDD e 10 ou 11 dígitos."
    }

    conditional {
      if ($input.profile_cpf != null && $input.profile_cpf != "") {
        var.update $cpf_digits {
          value = $input.profile_cpf|regex_replace:"[^0-9]":""
        }

      }
    }

    db.query user {
      where = $db.user.email == $input.profile_email && $db.user.id != $auth.id
      return = {type: "single"}
    } as $existing_email

    precondition ($existing_email == null) {
      error_type = "inputerror"
      error = "Este e-mail já está associado a outra conta."
    }

    conditional {
      if ($cpf_digits != "") {
        db.query contact {
          where = $db.contact.cpf_normalized == $cpf_digits
          return = {type: "list"}
        } as $existing_contact_cpf

        precondition (($existing_contact_cpf|count) == 0) {
          error_type = "inputerror"
          error = "Já existe um cadastro com este CPF."
        }

        db.query user {
          where = $db.user.cpf == $cpf_digits && $db.user.id != $auth.id
          return = {type: "list"}
        } as $existing_user_cpf

        precondition (($existing_user_cpf|count) == 0) {
          error_type = "inputerror"
          error = "Já existe um cadastro com este CPF."
        }
      }
    }

    db.edit user {
      field_name = "id"
      field_value = $auth.id
      data = {
        name  : $input.profile_name
        email : $input.profile_email
        phone : $phone_digits
        cpf   : $cpf_digits
      }
    } as $user
  }

  response = {
    id     : $user.id
    name   : $user.name
    email  : $user.email
    phone  : $user.phone
    cpf    : $user.cpf
    role   : $user.role
    status : $user.status
  }
  guid = "opv2jIuWyN9TgvL85ESPfVJDf6E"
}
