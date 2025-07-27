<#import "template.ftl" as layout>
<@layout.registrationLayout displayMessage=false; section>
    <#if section = "header">
        ${msg("emailVerifiedTitle", msg("emailVerifiedTitle", "Email verified"))}
    <#elseif section = "form">
        <div id="kc-info-message">
            <p class="instruction">${message.summary?no_esc}</p>
            
            <#-- Check if this is an email verification success message -->
            <#if message.summary?contains("verified") || messageType == 'success'>
                <script type="text/javascript">
                    // Configuration for redirect
                    const appUrl = '${client.rootUrl!"http://localhost:3000"}';
                    const redirectDelay = 3000; // 3 seconds
                    
                    // Display countdown
                    let countdown = redirectDelay / 1000;
                    const countdownElement = document.createElement('p');
                    countdownElement.className = 'instruction';
                    countdownElement.style.marginTop = '20px';
                    countdownElement.textContent = 'Redirecting to application in ' + countdown + ' seconds...';
                    document.getElementById('kc-info-message').appendChild(countdownElement);
                    
                    // Update countdown
                    const interval = setInterval(function() {
                        countdown--;
                        if (countdown > 0) {
                            countdownElement.textContent = 'Redirecting to application in ' + countdown + ' seconds...';
                        } else {
                            countdownElement.textContent = 'Redirecting...';
                        }
                    }, 1000);
                    
                    // Perform redirect
                    setTimeout(function() {
                        clearInterval(interval);
                        window.location.href = appUrl;
                    }, redirectDelay);
                </script>
                
                <#if client?? && client.baseUrl?has_content>
                    <div style="margin-top: 30px;">
                        <p><a id="backToApplication" href="${client.baseUrl}">
                            ${kcSanitize(msg("backToApplication", "Go to Application"))?no_esc}
                        </a></p>
                    </div>
                <#else>
                    <div style="margin-top: 30px;">
                        <p><a id="backToApplication" href="http://localhost:3000">
                            ${kcSanitize(msg("backToApplication", "Go to Application"))?no_esc}
                        </a></p>
                    </div>
                </#if>
            <#else>
                <#if skipLink??>
                <#else>
                    <#if pageRedirectUri?has_content>
                        <p><a href="${pageRedirectUri}">${kcSanitize(msg("backToApplication"))?no_esc}</a></p>
                    <#elseif actionUri?has_content>
                        <p><a href="${actionUri}">${kcSanitize(msg("proceedWithAction"))?no_esc}</a></p>
                    <#elseif (client.baseUrl)?has_content>
                        <p><a href="${client.baseUrl}">${kcSanitize(msg("backToApplication"))?no_esc}</a></p>
                    </#if>
                </#if>
            </#if>
        </div>
    </#if>
</@layout.registrationLayout>
