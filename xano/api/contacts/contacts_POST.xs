query "contacts" verb=POST {
  api_group = "Contacts"
  auth = "user"

  input {
    text name filters=trim
    text phone filters=trim
    text cpf? filters=trim
    text birth_date? filters=trim
    text email? filters=trim|lower
    enum source {
      values = ["whatsapp", "indicacao", "instagram", "ligacao", "outra"]
    }
    text notes? filters=trim
    timestamp first_contact_at
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "professional"}
    } as $role_check

    var $normalized_phone {
      value = $input.phone
    }

    var $normalized_cpf {
      value = ""
    }

    conditional {
      if ($input.cpf != null && $input.cpf != "") {
        var.update $normalized_cpf {
          value = $input.cpf|regex_replace:"[^0-9]":""
        }
      }
    }

    precondition ($input.name != "" && ($input.name|strlen) <= 120) {
      error_type = "inputerror"
      error = "Informe um nome válido de até 120 caracteres."
    }

    precondition (($normalized_phone|strlen) >= 10 && ($normalized_phone|strlen) <= 11) {
      error_type = "inputerror"
      error = "Informe um telefone válido."
    }

    precondition ($input.birth_date == null || $input.birth_date == "" || ($input.birth_date|strlen) == 10) {
      error_type = "inputerror"
      error = "Informe uma data de nascimento válida."
    }

    precondition ($input.birth_date == null || $input.birth_date == "" || $input.birth_date <= (now|format_timestamp:"Y-m-d":"America/Sao_Paulo")) {
      error_type = "inputerror"
      error = "A data de nascimento não pode estar no futuro."
    }

    precondition ($input.email == null || $input.email == "" || ($input.email|strlen) <= 254) {
      error_type = "inputerror"
      error = "Informe um e-mail válido."
    }

    precondition (
      ($input.first_contact_at|format_timestamp:"Y-m-d":"America/Sao_Paulo")
      <= (now|format_timestamp:"Y-m-d":"America/Sao_Paulo")
    ) {
      error_type = "inputerror"
      error = "A data do primeiro contato não pode estar no futuro."
    }

    precondition ($input.notes == null || ($input.notes|strlen) <= 1000) {
      error_type = "inputerror"
      error = "As observações devem ter no máximo 1000 caracteres."
    }

    db.query contact {
      where = $db.contact.phone_normalized == $normalized_phone
      return = {type: "list"}
    } as $duplicates

    precondition (($duplicates|count) == 0) {
      error_type = "inputerror"
      error = "Este telefone já está cadastrado."
    }

    conditional {
      if ($normalized_cpf != "") {
        db.query contact {
          where = $db.contact.cpf_normalized == $normalized_cpf
          return = {type: "list"}
        } as $cpf_duplicates

        precondition (($cpf_duplicates|count) == 0) {
          error_type = "inputerror"
          error = "Já existe um cadastro com este CPF."
        }

        db.query user {
          where = $db.user.cpf == $normalized_cpf
          return = {type: "list"}
        } as $user_cpf_duplicates

        precondition (($user_cpf_duplicates|count) == 0) {
          error_type = "inputerror"
          error = "Já existe um cadastro com este CPF."
        }
      }
    }

    db.add contact {
      data = {
        created_at        : "now"
        updated_at        : "now"
        name              : $input.name
        phone             : $normalized_phone
        phone_normalized  : $normalized_phone
        cpf               : $normalized_cpf
        cpf_normalized    : $normalized_cpf
        birth_date        : $input.birth_date
        email             : $input.email
        source            : $input.source
        notes             : $input.notes
        status            : "active"
        first_contact_at  : $input.first_contact_at
      }
    } as $contact
  }

  response = $contact
  guid = "xTvXIF2TCIrrr7MZcJOjCgJv3NA"
}
