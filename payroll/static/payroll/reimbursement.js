function reimbursementConfirm(params, target, approve = false) {
  event.preventDefault();
  event.stopPropagation();
  const options = {
    text: params,
    icon: "question",
    showCancelButton: true,
    confirmButtonColor: "#008000",
    cancelButtonColor: "#d33",
    confirmButtonText: "Confirm",
    cancelButtonText: "Close",
  };
  const hasRejectField = !approve && $(`${target} [name=reject_reason]`).length;
  if (hasRejectField) {
    options.input = "textarea";
    options.inputAttributes = { maxlength: 250 };
    options.inputValidator = (value) => {
      if (!value) {
        return "Rejection reason is required";
      }
    };
  }
  Swal.fire(options).then((result) => {
    if (result.isConfirmed) {
      if (approve) {
        $(`${target} [name=amount]`).attr("required", true);
      } else if (hasRejectField) {
        $(`${target} [name=reject_reason]`).val(result.value);
      }
      $(target + "Button").click();
    }
  });
}
