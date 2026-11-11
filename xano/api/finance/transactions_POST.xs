// Records a positive financial movement in the authenticated barbershop ledger.
query "finance/transactions" verb=POST {
  api_group = "Finance"
  auth = "user"

  input {
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

    db.add finance_transaction {
      data = {
        created_at: "now"
        updated_at: "now"
        type: $input.type
        amount: $input.amount
        title: $input.title
        detail: $input.detail
        occurred_at: $input.occurred_at
        created_by: $auth.id
      }
    } as $transaction
  }

  response = $transaction
  guid = "6sRHTaMxniK8N64SsGw4xEh-pMY"
}
