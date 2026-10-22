query "contacts/{contact_id}" verb=PATCH {
  api_group = "Contacts"
  auth = "user"

  input {
    int contact_id
    text name filters=trim
    text phone filters=trim
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

    db.get contact {
      field_name = "id"
      field_value = $input.contact_id
    } as $existing_contact

    precondition ($existing_contact != null) {
      error_type = "inputerror"
      error = "Contato não encontrado."
    }

    var $normalized_phone {
      value = $input.phone
    }

    precondition ($input.name != "" && ($input.name|strlen) <= 120) {
      error_type = "inputerror"
      error = "Informe um nome válido de até 120 caracteres."
    }

    precondition (($normalized_phone|strlen) >= 10 && ($normalized_phone|strlen) <= 11) {
      error_type = "inputerror"
      error = "Informe um telefone válido."
    }

    precondition ($input.first_contact_at <= "now") {
      error_type = "inputerror"
      error = "A data do primeiro contato não pode estar no futuro."
    }

    precondition ($input.notes == null || ($input.notes|strlen) <= 1000) {
      error_type = "inputerror"
      error = "As observações devem ter no máximo 1000 caracteres."
    }

    db.query contact {
      where = $db.contact.phone_normalized == $normalized_phone && $db.contact.status == "active" && $db.contact.id != $input.contact_id
      return = {type: "list"}
    } as $duplicates

    precondition (($duplicates|count) == 0) {
      error_type = "inputerror"
      error = "Este telefone já está cadastrado."
    }

    db.edit contact {
      field_name = "id"
      field_value = $input.contact_id
      data = {
        updated_at       : "now"
        name             : $input.name
        phone            : $normalized_phone
        phone_normalized : $normalized_phone
        source           : $input.source
        notes            : $input.notes
        first_contact_at : $input.first_contact_at
      }
    } as $contact
  }

  response = $contact
  guid = "dvVmSn3JSHX4eU7PPcpxMw70JvE"
}
