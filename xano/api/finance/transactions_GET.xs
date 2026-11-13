// Returns one server-paginated page of the shared financial ledger.
query "finance/transactions" verb=GET {
  api_group = "Finance"
  auth = "user"

  input {
    int page?=1
    bool include_cancelled?=false
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {
        user_id: $auth.id
        required_role: "professional"
      }
    } as $access_check

    precondition ($input.page >= 1) {
      error_type = "inputerror"
      error = "A página solicitada é inválida."
    }

    db.query finance_transaction {
      sort = {finance_transaction.occurred_at: "desc", finance_transaction.id: "desc"}
      return = {type: "list"}
    } as $all_transactions

    db.query finance_transaction {
      where = $db.finance_transaction.status == "cancelled"
      return = {type: "list"}
    } as $cancelled_transactions

    var $filtered_transactions {
      value = $all_transactions
    }

    conditional {
      if ($input.include_cancelled != true) {
        array.filter ($all_transactions) if ($this.status == "active") as $filtered_transactions
      }
    }

    var $total {
      value = $filtered_transactions|count
    }

    var $page_size {
      value = 3
    }

    var $page_offset {
      value = ($input.page - 1) * $page_size
    }

    var $page_transactions {
      value = $filtered_transactions|slice:$page_offset:$page_size
    }
  }

  response = {
    items: $page_transactions
    total: $total
    page: $input.page
    page_size: $page_size
    has_cancelled: (($cancelled_transactions|count) > 0)
  }
  guid = "K9mP3wL7xQ2vB6tR5aC1dF"
}
