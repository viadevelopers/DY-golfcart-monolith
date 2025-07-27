document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('kc-register-form');
    if (form) {
        form.addEventListener('submit', function(e) {
            const password = document.getElementById('password');
            const passwordConfirm = document.getElementById('password-confirm');
            
            if (password && passwordConfirm) {
                password.value = password.value.trim();
                passwordConfirm.value = passwordConfirm.value.trim();
            }
        });
        
        const passwordField = document.getElementById('password');
        const passwordConfirmField = document.getElementById('password-confirm');
        
        if (passwordConfirmField) {
            passwordConfirmField.addEventListener('paste', function(e) {
                setTimeout(function() {
                    passwordConfirmField.value = passwordConfirmField.value.trim();
                }, 10);
            });
        }
    }
});