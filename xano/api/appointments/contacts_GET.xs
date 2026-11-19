// Returns active contacts for booking appointments in the authenticated barbershop.
query "appointments/contacts" verb=GET {
  api_group = "Appointments"
  auth = "user"

  input {
    int page?=1
    int page_size?=50
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {
        user_id: $auth.id
        required_role: "professional"
      }
    } as $role_check

    precondition ($input.page >= 1 && $input.page_size >= 1 && $input.page_size <= 50) {
      error_type = "inputerror"
      error = "Página ou tamanho de página inválido."
    }

    db.query contact {
      where = (
        (
          $db.contact.barbershop_id == $role_check.barbershop_id
          || ($role_check.include_legacy_rows == true && $db.contact.barbershop_id == null)
        )
        && $db.contact.status == "active"
        && ($role_check.role == "admin" || $db.contact.professional_id == $auth.id)
      )
      sort = {contact.name: "asc", contact.id: "asc"}
      output = ["id", "name", "phone"]
      return = {type: "list"}
    } as $all_contacts

    var $total_contacts {
      value = $all_contacts|count
    }

    var $page_offset {
      value = ($input.page - 1) * $input.page_size
    }

    var $page_contacts {
      value = $all_contacts|slice:$page_offset:$input.page_size
    }
  }

  response = {
    items: $page_contacts
    total: $total_contacts
    page: $input.page
    page_size: $input.page_size
  }
  guid = "aPp01nTm3ntC0nt4ctG3t2026"
}
