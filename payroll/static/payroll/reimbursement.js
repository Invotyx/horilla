function reimbursementConfirm(params, target, approve = false) {
  event.preventDefault();
  event.stopPropagation();
  const $card = $(target);
  const $form = $card.find('form').first();
  const hasRejectField = !approve && $(`${target} [name=reject_reason]`).length;
  const hasFinance = approve && $(`${target} [name=finance_comment]`).length > 0;

  if (approve && hasFinance) {
    // Finance-specific approval modal: capture amount + comment in the same dialog
    const claimed = parseFloat(($form.attr('data-claimed-total') || '0')) || 0;
    const currentAmt = parseFloat(($(`${target} [name=amount]`).val() || '0')) || 0;
    Swal.fire({
      title: params,
      html: `
        <div style="text-align:left">
          <label style="display:block; margin-bottom:4px;">Approved Payment</label>
          <input id="swal-amount" type="number" min="0" step="0.01" class="swal2-input" style="width:100%" value="${currentAmt.toFixed(2)}" />
          ${claimed ? `<div style="font-size:12px;color:#666;margin-top:-10px">Total Claimed: ${claimed.toFixed(2)}</div>` : ''}
          <label style="display:block; margin:8px 0 4px">Finance Comment</label>
          <textarea id="swal-comment" class="swal2-textarea" maxlength="500" style="width:100%"></textarea>
        </div>
      `,
      focusConfirm: false,
      showCancelButton: true,
      confirmButtonColor: "#008000",
      cancelButtonColor: "#d33",
      confirmButtonText: "Confirm",
      cancelButtonText: "Close",
      preConfirm: () => {
        const amt = parseFloat(document.getElementById('swal-amount').value || '0') || 0;
        const comment = (document.getElementById('swal-comment').value || '').trim();
        if (claimed && amt > claimed) {
          Swal.showValidationMessage('Approved payment cannot exceed claimed total.');
          return false;
        }
        if (claimed && amt < claimed && !comment) {
          Swal.showValidationMessage('Finance comment is required when approving a partial amount.');
          return false;
        }
        return { amt, comment };
      },
    }).then((result) => {
      if (result.isConfirmed && result.value) {
        const { amt, comment } = result.value;
        const $amount = $(`${target} [name=amount]`);
        const $comment = $(`${target} [name=finance_comment]`);
        if ($amount.length) { $amount.val(amt.toFixed(2)); $amount.attr('required', true); }
        if ($comment.length) { $comment.val(comment); }
        $(target + "Button").click();
      }
    });
    return;
  }

  const options = {
    text: params,
    icon: "question",
    showCancelButton: true,
    confirmButtonColor: "#008000",
    cancelButtonColor: "#d33",
    confirmButtonText: "Confirm",
    cancelButtonText: "Close",
  };
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
