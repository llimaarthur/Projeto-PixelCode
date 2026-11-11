// Updates a financial movement while preserving its prior values in the audit ledger.
query "finance/transactions/{transaction_id}" verb=PATCH {
  api_group = "Finance"
  auth = "user"

  input {
    int transaction_id
    enum type {
      values = ["income", "expense"]
    }
    decimal amount
    text title filters=trim
    text detail? filters=trim
    timestamp occurred_at
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
      error = "Uma movimentação estornada não pode ser editada."
    }

    precondition ($input.amount > 0 && $input.amount == ($input.amount|round:2)) {
      error_type = "inputerror"
      error = "O valor deve ser positivo e ter no máximo duas casas decimais."
    }

    precondition ($input.title != "" && ($input.title|strlen) <= 100) {
      error_type = "inputerror"
      error = "Informe uma descrição com até 100 caracteres."
    }

    precondition ($input.detail == null || ($input.detail|strlen) <= 250) {
      error_type = "inputerror"
      error = "O detalhe deve ter até 250 caracteres."
    }

    precondition ($input.occurred_at <= now) {
      error_type = "inputerror"
      error = "A data da movimentação não pode estar no futuro."
    }

    db.add finance_transaction_revision {
      data = {
        changed_at: "now"
        action: "edited"
        transaction_id: $existing_transaction.id
        changed_by: $auth.id
        previous_type: $existing_transaction.type
        previous_amount: $existing_transaction.amount
        previous_title: $existing_transaction.title
        previous_detail: $existing_transaction.detail
        previous_occurred_at: $existing_transaction.occurred_at
      }
    } as $revision

    db.edit finance_transaction {
      field_name = "id"
      field_value = $existing_transaction.id
      data = {
        updated_at: "now"
        type: $input.type
        amount: $input.amount
        title: $input.title
        detail: $input.detail
        occurred_at: $input.occurred_at
      }
    } as $transaction
  }

  response = $transaction
  guid = "A6kL3pQ9vR2xT7mN4bC5dF"
}
