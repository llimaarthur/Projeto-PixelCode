// Enforces the barbershop's weekly opening hours in its UTC-3 local time.
function "Quick Start/validate_working_interval" {
  input {
    timestamp start_at
    timestamp end_at
  }

  stack {
    precondition ($input.start_at < $input.end_at) {
      error_type = "inputerror"
      error = "O fim do intervalo deve ser posterior ao início."
    }

    var $weekday {
      value = ($input.start_at|format_timestamp:"N":"America/Sao_Paulo")|to_int
    }

    var $start_hhmm {
      value = ($input.start_at|format_timestamp:"Hi":"America/Sao_Paulo")|to_int
    }

    var $end_hhmm {
      value = ($input.end_at|format_timestamp:"Hi":"America/Sao_Paulo")|to_int
    }

    var $start_minute {
      value = ($input.start_at|format_timestamp:"i":"America/Sao_Paulo")|to_int
    }

    var $start_second {
      value = ($input.start_at|format_timestamp:"s":"America/Sao_Paulo")|to_int
    }

    precondition (
      ($input.start_at|format_timestamp:"Y-m-d":"America/Sao_Paulo")
      == ($input.end_at|format_timestamp:"Y-m-d":"America/Sao_Paulo")
    ) {
      error_type = "inputerror"
      error = "O atendimento deve começar e terminar no mesmo dia."
    }

    precondition (($start_minute == 0 || $start_minute == 30) && $start_second == 0) {
      error_type = "inputerror"
      error = "Os horários devem começar em intervalos de 30 minutos."
    }

    precondition (
      ($weekday >= 1 && $weekday <= 5 && (
        ($start_hhmm >= 900 && $end_hhmm <= 1200)
        || ($start_hhmm >= 1300 && $end_hhmm <= 1900)
      ))
      || ($weekday == 6 && $start_hhmm >= 900 && $end_hhmm <= 1400)
    ) {
      error_type = "inputerror"
      error = "O intervalo solicitado está fora do expediente da barbearia."
    }
  }

  response = true
  guid = "d3F8hJ1kL4mN7pQ0rT2vW5xY9aB"
}
