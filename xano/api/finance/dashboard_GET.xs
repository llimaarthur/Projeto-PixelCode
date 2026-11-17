// Returns the financial ledger for authenticated administrators and professionals.
query "finance/dashboard" verb=GET {
  api_group = "Finance"
  auth = "user"

  input {
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {
        user_id: $auth.id
        required_role: "professional"
      }
    } as $access_check

    db.query finance_transaction {
      where = (
        $db.finance_transaction.barbershop_id == $access_check.barbershop_id
        || ($access_check.include_legacy_rows == true && $db.finance_transaction.barbershop_id == null)
      )
      sort = {finance_transaction.occurred_at: "desc", finance_transaction.id: "desc"}
      return = {type: "list"}
    } as $transactions
  }

  response = {transactions: $transactions}
  guid = "622EtOTzVGNtEtU9rtP6MZEmueA"
}
