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
      } else {
        redirectToTokenForm();
      }
    });
  };

  var checkForOneTouch = function(request_id) {
    $.get("/payments/status?request_id=" + request_id, function(data) {
      if (data == "approved") {
        window.location.href = "/payments";
      } else if (data == "denied") {
        redirectToTokenForm();
      } else {
        setTimeout(checkForOneTouch(request_id), 2000);
      }
    });
  };

  var redirectToTokenForm = function() {
    alert("Authorization denied.");
    window.location.href = "/payments/send";
    // todo redirect to SMS form
  };
});
