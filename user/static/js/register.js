$(document).ready(function () {
    const csrfToken = $('input[name="csrfmiddlewaretoken"]').val();
    let button = $("#get-verify");
    button.click(function (event) {
        event.preventDefault();
        $.ajax({
            url: "/user/verify/",
            type: 'post',
            headers: {
                'X-CSRFToken': csrfToken  // Include the CSRF token in the headers
            },
            data: {
                email: $("#id_email").val(),
                page: window.location.pathname
            },
            dataType: 'json',
            success: function (res) {
                console.log(res);
                if (res.errors.email) {
                    $("#email-invalid-feedback").text(res.errors.email[0]);
                    $("#id_email").attr("class", "form-control is-invalid");
                } else {
                    button.attr("disabled", true);
                    $("#email-invalid-feedback").text("");
                    $("#id_email").attr("class", "form-control is-valid");
                    updateCountdown();
                }
            }
        });
    });

    function updateCountdown() {
        let seconds = 60;
        button.text(seconds + "s");

        function countdown() {
            if (seconds === 0) {
                // Enable the button
                button.attr("disabled", false);
                button.text("获取验证码");  // or display other content
            } else {
                seconds--;
                button.text(seconds + "s");
                setTimeout(countdown, 1000);
            }
        }

        countdown();
    }
});