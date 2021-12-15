#EB2-NIW Wait Time Analysis Based on We Greened Data

This code scrapes data from the I-140 approvals section of the [Chen Immigration website](https://www.wegreened.com/eb1_niw_approvals) and processes it to determine current wait times by service center. 

###Steps:

1. Download PDF files from the Chen Immigration website
2. Generate PNG images necessary for parsing by `pytesseract`
3. Parse images using `pytesseract` and generate `I140Form` objects
4. Generate dataset based on `I140Form` features such as `notice date`, `receipt date`, `priority date`, and `NIW flag` indicating whether a form is for an NIW application
5. Generate yearly wait time distribution and plot for 2017+
6. Send plot as attachment to desired recipients via `SendGrid`

###Installation and Running Instructions:
Navigate to the location of your codebase in your terminal and run the following commands:
1. `python setup.py install`
2. `export SENDGRID_API_KEY=<YOUR_API>` to run the email client _[Optional]_ 
3. `python -m src <SERVICE_CENTER>` where `<SERVICE_CENTER>` is either `SRC` for the Texas Service Center or `LIN` for the Nebraska Service Center