from email.message import EmailMessage
import ssl
import smtplib


def send_strategy_signal(email, signal_str, strategy_type, strategy_symbol):
    email_from = "adi.profile1@gmail.com"
    email_password = "gwaryitmlyzygepr"  # Consider using environment variables for security
    email_to = email

    subject = "QuarksFinance: Your strategy was executed!"

    body = f"""
<!doctype html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
  <head>
    <title></title>
    <!--[if !mso]><!-->
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <!--<![endif]-->
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style type="text/css">
      #outlook a {{ padding:0; }}
      body {{ margin:0;padding:0;-webkit-text-size-adjust:100%;-ms-text-size-adjust:100%; }}
      table, td {{ border-collapse:collapse;mso-table-lspace:0pt;mso-table-rspace:0pt; }}
      img {{ border:0;height:auto;line-height:100%; outline:none;text-decoration:none;-ms-interpolation-mode:bicubic; }}
      p {{ display:block;margin:13px 0; }}
    </style>
    <!--[if mso]>
    <noscript>
    <xml>
    <o:OfficeDocumentSettings>
      <o:AllowPNG/>
      <o:PixelsPerInch>96</o:PixelsPerInch>
    </o:OfficeDocumentSettings>
    </xml>
    </noscript>
    <![endif]-->
    <!--[if lte mso 11]>
    <style type="text/css">
      .mj-outlook-group-fix {{ width:100% !important; }}
    </style>
    <![endif]-->

      <!--[if !mso]><!-->
        <link href="https://fonts.googleapis.com/css?family=Ubuntu:300,400,500,700" rel="stylesheet" type="text/css">
<link href="https://fonts.googleapis.com/css?family=Cabin:400,700" rel="stylesheet" type="text/css">
        <style type="text/css">
          @import url(https://fonts.googleapis.com/css?family=Ubuntu:300,400,500,700);
@import url(https://fonts.googleapis.com/css?family=Cabin:400,700);
        </style>
      <!--<![endif]-->



    <style type="text/css">
      @media only screen and (min-width:480px) {{
        .mj-column-per-100 {{ width:100% !important; max-width: 100%; }} }}
    </style>
    <style media="screen and (min-width:480px)">
      .moz-text-html .mj-column-per-100 {{ width:100% !important; max-width: 100%; }}
    </style>


    <style type="text/css">



    @media only screen and (max-width:479px) {{
      table.mj-full-width-mobile {{ width: 100% !important; }}
      td.mj-full-width-mobile {{ width: auto !important; }}
    }}

    </style>
    <style type="text/css">
    .hide_on_mobile {{ display: none !important;}}
        @media only screen and (min-width: 480px) {{ .hide_on_mobile {{ display: block !important;}} }}
        .hide_section_on_mobile {{ display: none !important;}}
        @media only screen and (min-width: 480px) {{
            .hide_section_on_mobile {{
                display: table !important;
            }}

            div.hide_section_on_mobile {{
                display: block !important;
            }}
        }}
        .hide_on_desktop {{ display: block !important;}}
        @media only screen and (min-width: 480px) {{ .hide_on_desktop {{ display: none !important;}} }}
        .hide_section_on_desktop {{
            display: table !important;
            width: 100%;
        }}
        @media only screen and (min-width: 480px) {{ .hide_section_on_desktop {{ display: none !important;}} }}

          p, h1, h2, h3 {{
              margin: 0px;
          }}

          ul, li, ol {{
            font-size: 11px;
            font-family: Ubuntu, Helvetica, Arial;
          }}

          a {{
              text-decoration: none;
              color: inherit;
          }}

        @media only screen and (max-width:480px) {{
            .mj-column-per-100 {{ width:100%!important; max-width:100%!important; }}.mj-column-per-100 > .mj-column-per-100 {{ width:100%!important; max-width:100%!important; }}
        }}

        .mj-column-per-100 [class^="mj-column-per-"] {{
            line-height: normal;
        }}
    </style>

  </head>
  <body style="word-spacing:normal;background-color:#FFFFFF;">


      <div style="background-color:#FFFFFF;">


      <!--[if mso | IE]><table align="center" border="0" cellpadding="0" cellspacing="0" class="" role="presentation" style="width:600px;" width="600" ><tr><td style="line-height:0px;font-size:0px;mso-line-height-rule:exactly;"><![endif]-->


      <div style="margin:0px auto;max-width:600px;">

        <table align="center" border="0" cellpadding="0" cellspacing="0" role="presentation" style="width:100%;">
          <tbody>
            <tr>
              <td style="direction:ltr;font-size:0px;padding:9px 0px 9px 0px;text-align:center;">
                <!--[if mso | IE]><table role="presentation" border="0" cellpadding="0" cellspacing="0"><tr><td class="" style="vertical-align:top;width:600px;" ><![endif]-->

      <div class="mj-column-per-100 mj-outlook-group-fix" style="font-size:0px;text-align:left;direction:ltr;display:inline-block;vertical-align:top;width:100%;">

      <table border="0" cellpadding="0" cellspacing="0" role="presentation" style="vertical-align:top;" width="100%">
        <tbody>

              <tr>
                <td align="center" style="font-size:0px;padding:0px 0px 0px 0px;word-break:break-word;">

      <table border="0" cellpadding="0" cellspacing="0" role="presentation" style="border-collapse:collapse;border-spacing:0px;">
        <tbody>
          <tr>
            <td style="width:65px;">

      <img src="https://thecodeworks.in/logoQF2.png" style="border:0;border-radius:0px 0px 0px 0px;display:block;outline:none;text-decoration:none;height:auto;width:100%;font-size:13px;" width="65" height="auto">

            </td>
          </tr>
        </tbody>
      </table>

                </td>
              </tr>

        </tbody>
      </table>

      </div>

          <!--[if mso | IE]></td></tr></table><![endif]-->
              </td>
            </tr>
          </tbody>
        </table>

      </div>


      <!--[if mso | IE]></td></tr></table><table align="center" border="0" cellpadding="0" cellspacing="0" class="" role="presentation" style="width:600px;" width="600" ><tr><td style="line-height:0px;font-size:0px;mso-line-height-rule:exactly;"><![endif]-->


      <div style="margin:0px auto;max-width:600px;">

        <table align="center" border="0" cellpadding="0" cellspacing="0" role="presentation" style="width:100%;">
          <tbody>
            <tr>
              <td style="direction:ltr;font-size:0px;padding:10px 0px 10px 0px;text-align:center;">
                <!--[if mso | IE]><table role="presentation" border="0" cellpadding="0" cellspacing="0"><tr><td class="" style="vertical-align:top;width:600px;" ><![endif]-->

      <div class="mj-column-per-100 mj-outlook-group-fix" style="font-size:0px;text-align:left;direction:ltr;display:inline-block;vertical-align:top;width:100%;">

      <table border="0" cellpadding="0" cellspacing="0" role="presentation" style="vertical-align:top;" width="100%">
        <tbody>

              <tr>
                <td align="center" style="font-size:0px;padding:0px 0px 0px 0px;word-break:break-word;">

      <table border="0" cellpadding="0" cellspacing="0" role="presentation" style="border-collapse:collapse;border-spacing:0px;">
        <tbody>
          <tr>
            <td style="width:296px;">

      <img src="https://thecodeworks.in/QuarksFinance.png" style="border:0;border-radius:0px 0px 0px 0px;display:block;outline:none;text-decoration:none;height:auto;width:100%;font-size:13px;" width="296" height="auto">

            </td>
          </tr>
        </tbody>
      </table>

                </td>
              </tr>

        </tbody>
      </table>

      </div>

          <!--[if mso | IE]></td></tr></table><![endif]-->
              </td>
            </tr>
          </tbody>
        </table>

      </div>


      <!--[if mso | IE]></td></tr></table><table align="center" border="0" cellpadding="0" cellspacing="0" class="" role="presentation" style="width:600px;" width="600" ><tr><td style="line-height:0px;font-size:0px;mso-line-height-rule:exactly;"><![endif]-->


      <div style="margin:0px auto;max-width:600px;">

        <table align="center" border="0" cellpadding="0" cellspacing="0" role="presentation" style="width:100%;">
          <tbody>
            <tr>
              <td style="direction:ltr;font-size:0px;padding:10px 0px 10px 0px;text-align:center;">
                <!--[if mso | IE]><table role="presentation" border="0" cellpadding="0" cellspacing="0"><tr><td class="" style="vertical-align:top;width:600px;" ><![endif]-->

      <div class="mj-column-per-100 mj-outlook-group-fix" style="font-size:0px;text-align:left;direction:ltr;display:inline-block;vertical-align:top;width:100%;">

      <table border="0" cellpadding="0" cellspacing="0" role="presentation" style="vertical-align:top;" width="100%">
        <tbody>

              <tr>
                <td align="center" style="font-size:0px;padding:10px 10px;padding-top:10px;padding-right:10px;word-break:break-word;">

      <p style="font-family: Helvetica, Arial, sans-serif; border-top: solid 1px #000000; font-size: 1px; margin: 0px auto; width: 100%;">
      </p>

      <!--[if mso | IE]><table align="center" border="0" cellpadding="0" cellspacing="0" style="border-top:solid 1px #000000;font-size:1px;margin:0px auto;width:580px;" role="presentation" width="580px" ><tr><td style="height:0;line-height:0;"> &nbsp;
</td></tr></table><![endif]-->


                </td>
              </tr>

        </tbody>
      </table>

      </div>

          <!--[if mso | IE]></td></tr></table><![endif]-->
              </td>
            </tr>
          </tbody>
        </table>

      </div>


      <!--[if mso | IE]></td></tr></table><table align="center" border="0" cellpadding="0" cellspacing="0" class="" role="presentation" style="width:600px;" width="600" ><tr><td style="line-height:0px;font-size:0px;mso-line-height-rule:exactly;"><![endif]-->


      <div style="margin:0px auto;max-width:600px;">

        <table align="center" border="0" cellpadding="0" cellspacing="0" role="presentation" style="width:100%;">
          <tbody>
            <tr>
              <td style="direction:ltr;font-size:0px;padding:10px 0px 10px 0px;text-align:center;">
                <!--[if mso | IE]><table role="presentation" border="0" cellpadding="0" cellspacing="0"><tr><td class="" style="vertical-align:top;width:600px;" ><![endif]-->

      <div class="mj-column-per-100 mj-outlook-group-fix" style="font-size:0px;text-align:left;direction:ltr;display:inline-block;vertical-align:top;width:100%;">

      <table border="0" cellpadding="0" cellspacing="0" role="presentation" style="vertical-align:top;" width="100%">
        <tbody>

              <tr>
                <td align="left" style="font-size:0px;padding:15px 15px 15px 15px;word-break:break-word;">

      <div style="font-family:Ubuntu, Helvetica, Arial, sans-serif;font-size:13px;line-height:1.5;text-align:left;color:#000000;"><p style="font-family: Helvetica, Arial, sans-serif; font-size: 11px; text-align: center;"><span style="font-size: 19px; color: rgb(52, 73, 94);"><strong>Your strategy was executed!</strong></span></p></div>

                </td>
              </tr>

        </tbody>
      </table>

      </div>

          <!--[if mso | IE]></td></tr></table><![endif]-->
              </td>
            </tr>
          </tbody>
        </table>

      </div>


      <!--[if mso | IE]></td></tr></table><table align="center" border="0" cellpadding="0" cellspacing="0" class="" role="presentation" style="width:600px;" width="600" ><tr><td style="line-height:0px;font-size:0px;mso-line-height-rule:exactly;"><![endif]-->


      <div style="margin:0px auto;max-width:600px;">

        <table align="center" border="0" cellpadding="0" cellspacing="0" role="presentation" style="width:100%;">
          <tbody>
            <tr>
              <td style="direction:ltr;font-size:0px;padding:10px 0px 10px 0px;text-align:center;">
                <!--[if mso | IE]><table role="presentation" border="0" cellpadding="0" cellspacing="0"><tr><td class="" style="vertical-align:top;width:600px;" ><![endif]-->

      <div class="mj-column-per-100 mj-outlook-group-fix" style="font-size:0px;text-align:left;direction:ltr;display:inline-block;vertical-align:top;width:100%;">

      <table border="0" cellpadding="0" cellspacing="0" role="presentation" style="vertical-align:top;" width="100%">
        <tbody>

              <tr>
                <td align="left" style="font-size:0px;padding:15px 15px 15px 15px;word-break:break-word;">

      <div style="font-family:Ubuntu, Helvetica, Arial, sans-serif;font-size:13px;line-height:1.5;text-align:left;color:#000000;"><p style="font-family: Helvetica, Arial, sans-serif; font-size: 11px; text-align: center;"><span style="font-size: 16px; color: rgb(0, 0, 0);">Strategy: {strategy_type} ON Symbol: {strategy_symbol}</span></p></div>

                </td>
              </tr>

        </tbody>
      </table>

      </div>

          <!--[if mso | IE]></td></tr></table><![endif]-->
              </td>
            </tr>
          </tbody>
        </table>

      </div>


      <!--[if mso | IE]></td></tr></table><table align="center" border="0" cellpadding="0" cellspacing="0" class="" role="presentation" style="width:600px;" width="600" ><tr><td style="line-height:0px;font-size:0px;mso-line-height-rule:exactly;"><![endif]-->


      <div style="margin:0px auto;max-width:600px;">

        <table align="center" border="0" cellpadding="0" cellspacing="0" role="presentation" style="width:100%;">
          <tbody>
            <tr>
              <td style="direction:ltr;font-size:0px;padding:10px 0px 10px 0px;text-align:center;">
                <!--[if mso | IE]><table role="presentation" border="0" cellpadding="0" cellspacing="0"><tr><td class="" style="vertical-align:top;width:600px;" ><![endif]-->

      <div class="mj-column-per-100 mj-outlook-group-fix" style="font-size:0px;text-align:left;direction:ltr;display:inline-block;vertical-align:top;width:100%;">

      <table border="0" cellpadding="0" cellspacing="0" role="presentation" style="vertical-align:top;" width="100%">
        <tbody>

              <tr>
                <td align="left" style="font-size:0px;padding:15px 15px 15px 15px;word-break:break-word;">

      <div style="font-family:Ubuntu, Helvetica, Arial, sans-serif;font-size:13px;line-height:1.5;text-align:left;color:#000000;"><p style="font-family: Helvetica, Arial, sans-serif; font-size: 11px; text-align: center;"><span style="font-size: 26px; color: rgb(45, 194, 107);">Signal: {signal_str}</span></p></div>

                </td>
              </tr>

        </tbody>
      </table>

      </div>

          <!--[if mso | IE]></td></tr></table><![endif]-->
              </td>
            </tr>
          </tbody>
        </table>

      </div>


      <!--[if mso | IE]></td></tr></table><table align="center" border="0" cellpadding="0" cellspacing="0" class="" role="presentation" style="width:600px;" width="600" ><tr><td style="line-height:0px;font-size:0px;mso-line-height-rule:exactly;"><![endif]-->


      <div style="margin:0px auto;max-width:600px;">

        <table align="center" border="0" cellpadding="0" cellspacing="0" role="presentation" style="width:100%;">
          <tbody>
            <tr>
              <td style="direction:ltr;font-size:0px;padding:10px 0px 10px 0px;text-align:center;">
                <!--[if mso | IE]><table role="presentation" border="0" cellpadding="0" cellspacing="0"><tr><td class="" style="vertical-align:top;width:600px;" ><![endif]-->

      <div class="mj-column-per-100 mj-outlook-group-fix" style="font-size:0px;text-align:left;direction:ltr;display:inline-block;vertical-align:top;width:100%;">

      <table border="0" cellpadding="0" cellspacing="0" role="presentation" style="vertical-align:top;" width="100%">
        <tbody>

              <tr>
                <td style="font-size:0px;word-break:break-word;">

      <div style="height:50px;line-height:50px;">&#8202;</div>

                </td>
              </tr>

        </tbody>
      </table>

      </div>

          <!--[if mso | IE]></td></tr></table><![endif]-->
              </td>
            </tr>
          </tbody>
        </table>

      </div>


      <!--[if mso | IE]></td></tr></table><![endif]-->


      </div>


<div style="color: #ccc; font-size: 12px; width: 600px; margin: 15px auto; text-align: center;"><a href="https://wordtohtml.net/email/designer">Created with WordToHTML.net Email Designer</a></div>
</body>
</html>

    """


    em = EmailMessage()
    em["From"] = email_from
    em['To'] = email_to
    em["Subject"] = subject
    em.set_content(body, subtype="html")
    context = ssl.create_default_context()

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as smtp:
            smtp.login(email_from, email_password)
            smtp.sendmail(email_from, email_to, em.as_string())
        print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {str(e)}")



def send_forgot_password(email, code):
        email_from = "adi.profile1@gmail.com"
        email_password = "gwaryitmlyzygepr"
        email_to = email

        subject = "herring: Change your Password"

        body = f""" <!DOCTYPE html>
<html>
<head>
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Marcellus&display=swap');


</style>

</head>

    <body style="color:white;background-color:black;
font-family: 'Marcellus', serif;
text-align:center;">

    <h1 style="color:#c91a1a;
font-family: 'DM Serif Display', serif;
text-align:center;
font-size:70px;">
        herring
    </h1>    
    <h2 "color:white;"> <strong> Change your Password </strong></h2>

    <h2 style="color:white;">    
        Here's your verification code to change your password
    </h2>
    <h1 style="color:white;">
        {code}
    </h1>
    </body>
    </html>
        """

        em = EmailMessage()
        em["From"] = email_from
        em['To'] = email_to
        em["Subject"] = subject
        em.set_content(body, subtype="html")
        context = ssl.create_default_context()

        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as smtp:
                smtp.login(email_from, email_password)
                smtp.sendmail(email_from, email_to, em.as_string())



