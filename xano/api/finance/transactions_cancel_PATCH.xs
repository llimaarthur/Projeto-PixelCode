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

    db.get user {
      field_name = "id"
      field_value = $auth.id
      output = ["id", "role"]
    } as $actor

    precondition ($actor.role == "admin" || $existing_transaction.created_by == $auth.id) {
      error_type = "accessdenied"
      error = "Você só pode estornar movimentações registradas por você. Administradores podem estornar qualquer lançamento."
    }

    precondition (($input.reason|strlen) >= 3 && ($input.reason|strlen) <= 250) {
      error_type = "inputerror"
      error = "Informe um motivo para o estorno, com até 250 caracteres."
    }

    conditional {
      if ($existing_transaction.appointment_id != null) {
        precondition ($existing_transaction.appointment_status_before_payment != null) {
          error_type = "inputerror"
          error = "O agendamento vinculado não possui status de pagamento para restaurar."
        }

        db.get appointment {
          field_name = "id"
          field_value = $existing_transaction.appointment_id
        } as $linked_appointment

        precondition ($linked_appointment != null && $linked_appointment.status == "completed") {
          error_type = "inputerror"
          error = "O status do agendamento mudou e não pode ser restaurado automaticamente."
        }

        function.run "Quick Start/authorize_professional_scope" {
          input = {
            actor_id: $auth.id
            target_professional_id: $linked_appointment.professional_id
          }
        } as $appointment_scope_check

        db.edit appointment {
          field_name = "id"
          field_value = $linked_appointment.id
          data = {
            updated_at: "now"
            status: $existing_transaction.appointment_status_before_payment
          }
        } as $restored_appointment
      }
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
        previous_contact_id: $existing_transaction.contact_id
        previous_contact_name_snapshot: $existing_transaction.contact_name_snapshot
        previous_services_snapshot: $existing_transaction.services_snapshot
        previous_appointment_id: $existing_transaction.appointment_id
        previous_appointment_status: $existing_transaction.appointment_status_before_payment
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

  response = {
    transaction: $transaction
    appointment_id: $existing_transaction.appointment_id
    appointment_status: $existing_transaction.appointment_status_before_payment
  }
  guid = "H8mK3dQ2xV7nP4tL9aB6cR"
}
