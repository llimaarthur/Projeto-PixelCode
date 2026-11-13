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
    int contact_id?
    json service_ids?
    int appointment_id?
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

    var $services_snapshot {
      value = []
    }

    var $contact_name_snapshot {
      value = null
    }

    conditional {
      if ($input.contact_id != null) {
        precondition ($input.type == "income") {
          error_type = "inputerror"
          error = "Clientes e serviços só podem ser associados a uma receita."
        }

        db.get contact {
          field_name = "id"
          field_value = $input.contact_id
          output = ["id", "name", "status"]
        } as $contact

        precondition ($contact != null && $contact.status == "active") {
          error_type = "inputerror"
          error = "Selecione um cliente ativo."
        }

        var.update $contact_name_snapshot {
          value = $contact.name
        }
      }

    }

    conditional {
      if ($input.service_ids != null && ($input.service_ids|count) > 0) {
        precondition ($input.contact_id != null) {
          error_type = "inputerror"
          error = "Selecione um cliente para associar os serviços."
        }

        var $processed_service_ids {
          value = []
        }

        foreach ($input.service_ids) {
          each as serviceId {
            array.has ($processed_service_ids) if (`$this == $serviceId`) as $duplicate_service

            precondition ($duplicate_service == false) {
              error_type = "inputerror"
              error = "Não selecione o mesmo serviço mais de uma vez."
            }

            array.push $processed_service_ids {
              value = $serviceId
            }

            db.get service {
              field_name = "id"
              field_value = $serviceId
              output = ["id", "name", "price", "duration_minutes", "status"]
            } as $service

            precondition ($service != null && $service.status == "active") {
              error_type = "inputerror"
              error = "Um ou mais serviços não estão ativos ou não existem."
            }

            array.push $services_snapshot {
              value = $service
            }
          }
        }
      }
    }

    var $appointment_status_before_payment {
      value = null
    }

    var $appointment_status_after_payment {
      value = null
    }

    conditional {
      if ($input.appointment_id != null) {
        precondition ($input.type == "income" && $input.contact_id != null) {
          error_type = "inputerror"
          error = "Associe um cliente para vincular o pagamento a um agendamento."
        }

        db.get appointment {
          field_name = "id"
          field_value = $input.appointment_id
        } as $linked_appointment

        precondition ($linked_appointment != null) {
          error_type = "inputerror"
          error = "O agendamento vinculado não foi encontrado."
        }

        function.run "Quick Start/authorize_professional_scope" {
          input = {
            actor_id: $auth.id
            target_professional_id: $linked_appointment.professional_id
          }
        } as $appointment_scope_check

        precondition (
          $linked_appointment.contact_id == $input.contact_id
          && (
            $linked_appointment.status == "pending"
            || $linked_appointment.status == "confirmed"
          )
        ) {
          error_type = "inputerror"
          error = "Selecione um agendamento pendente ou confirmado do cliente escolhido."
        }

        db.query finance_transaction {
          where = (
            $db.finance_transaction.appointment_id == $linked_appointment.id
            && $db.finance_transaction.status == "active"
            && $db.finance_transaction.type == "income"
          )
          return = {type: "list"}
        } as $active_appointment_payments

        precondition (($active_appointment_payments|count) == 0) {
          error_type = "inputerror"
          error = "Este agendamento já possui um pagamento ativo."
        }

        var.update $appointment_status_before_payment {
          value = $linked_appointment.status
        }

        var.update $services_snapshot {
          value = $linked_appointment.services_snapshot
        }

        db.edit appointment {
          field_name = "id"
          field_value = $linked_appointment.id
          data = {
            updated_at: "now"
            status: "completed"
          }
        } as $completed_appointment

        var.update $appointment_status_after_payment {
          value = $completed_appointment.status
        }
      }
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
        contact_id: $input.contact_id
        contact_name_snapshot: $contact_name_snapshot
        services_snapshot: $services_snapshot
        appointment_id: $input.appointment_id
        appointment_status_before_payment: $appointment_status_before_payment
      }
    } as $transaction
  }

  response = {
    transaction: $transaction
    appointment_id: $input.appointment_id
    appointment_status: $appointment_status_after_payment
  }
  guid = "6sRHTaMxniK8N64SsGw4xEh-pMY"
}
