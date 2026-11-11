// Cancels a financial movement without deleting its ledger or audit history.
query "finance/transactions/{transaction_id}/cancel" verb=PATCH {
  api_group = "Finance"
  auth = "user"

  input {
    int transaction_id
    text reason filters=trim
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {
        user_id: $auth.id
        required_role: "professional"
      }
    } as $access_check

    db.get finance_transaction {
      field_name = "id"
      field_value = $input.transaction_id
    } as $existing_transaction

    precondition ($existing_transaction != null) {
      error_type = "inputerror"
      error = "Movimentação não encontrada."
    }

    precondition ($existing_transaction.status == "active") {
      error_type = "inputerror"
      error = "Esta movimentação já foi estornada."
    }

    precondition (($input.reason|strlen) >= 3 && ($input.reason|strlen) <= 250) {
      error_type = "inputerror"
      error = "Informe um motivo para o estorno, com até 250 caracteres."
    }

    db.add finance_transaction_revision {
      data = {
        changed_at: "now"
        action: "cancelled"
        transaction_id: $existing_transaction.id
        changed_by: $auth.id
        previous_type: $existing_transaction.type
        previous_amount: $existing_transaction.amount
        previous_title: $existing_transaction.title
        previous_detail: $existing_transaction.detail
        previous_occurred_at: $existing_transaction.occurred_at
        reason: $input.reason
      }
    } as $revision

    db.edit finance_transaction {
      field_name = "id"
      field_value = $existing_transaction.id
      data = {
        updated_at: "now"
        status: "cancelled"
        cancelled_at: "now"
        cancelled_by: $auth.id
        cancellation_reason: $input.reason
      }
    } as $transaction
  }

  response = $transaction
  guid = "H8mK3dQ2xV7nP4tL9aB6cR"
}
