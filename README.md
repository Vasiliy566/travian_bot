Simple travian bot to automatically grade mani villages.

Install:
`pip install travibot`

Usage:

1. Choose server you want to play
2. Create as many account as you want. To get new mail user external services like https://temp-mail.org/en/ and etc
3. Create list of your accounts - login + password (or save in file)
4. Install travibot via pip
5. Write simple script:
```
from src.travibot_Vasily566.main import run_travian

creds = [
    ("acc1_mail1@mail.mail", "password"),
    ("acc2_mail1@mail.mail", "password"),
]
run_travian(creds=creds)
```
Note!
In account settings you should:
1. Choose Russian language
2. Disable hints (first settings point)


