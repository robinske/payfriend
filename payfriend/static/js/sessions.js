$(document).ready(function() {
  $("#send-payment-form").submit(function(e) {
    e.preventDefault();
    formData = $(e.currentTarget).serialize();
    attemptOneTouchVerification(formData);
  });

  var attemptOneTouchVerification = function(form) {
    $.post("/payments/send", form, function(data) {
      if (data.success) {
        $(".auth-ot").fadeIn();
        checkForOneTouch(data.request_id);
      }
    });
  };

  var checkForOneTouch = function(request_id) {
    $.get("/payments/status?request_id=" + request_id, function(data) {
      if (data == "approved") {
        redirectWithMessage('/payments/', 'Your payment has been approved!')
      } else if (data == "denied") {
        redirectWithMessage('/payments/send', 'Your payment request has been denied.');
      } else {
        setTimeout(checkForOneTouch(request_id), 2000);
      }
    });
  };

  var redirectWithMessage = function(location, message) {
    var form = $("#redirect_to");
    $("#flash_message").val(message);
    form.attr('action', location)
    form.submit();
    // todo redirect to SMS form
  };
});
