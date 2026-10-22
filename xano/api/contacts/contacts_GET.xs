query "contacts" verb=GET {
  api_group = "Contacts"
  auth = "user"

  input {
    text search?
    enum status? {
      values = ["active", "inactive"]
    }
    enum source? {
      values = ["whatsapp", "indicacao", "instagram", "ligacao", "outra"]
    }
    int page?=1
    int page_size?=10
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "professional"}
    } as $role_check

    precondition ($input.page >= 1 && $input.page_size >= 1 && $input.page_size <= 50) {
      error_type = "inputerror"
      error = "Página ou tamanho de página inválido."
    }

    db.query contact {
      sort = {contact.name: "asc", contact.id: "asc"}
      return = {type: "list"}
    } as $all_contacts

    array.filter ($all_contacts) if (
      ($input.status == null || $this.status == $input.status)
      && ($input.source == null || $this.source == $input.source)
    ) as $filtered_by_fields

    var $matching_contacts {
      value = $filtered_by_fields
    }

    conditional {
      if ($input.search != null && $input.search != "") {
        var $normalized_search {
          value = $input.search|regex_replace:"[^0-9]":""
        }

        array.filter ($filtered_by_fields) if (
          $this.name|lower|contains:($input.search|lower)
          || ($normalized_search != "" && $this.phone_normalized|contains:$normalized_search)
        ) as $matching_contacts
      }
    }

    var $total_contacts {
      value = $matching_contacts|count
    }

    var $page_offset {
      value = ($input.page - 1) * $input.page_size
    }

    var $page_contacts {
      value = $matching_contacts|slice:$page_offset:$input.page_size
    }
  }

  response = {
    items     : $page_contacts
    total     : $total_contacts
    page      : $input.page
    page_size : $input.page_size
  }
  guid = "cNXs_GMtivtPTHEF8tUNHdaV7Ms"
}
