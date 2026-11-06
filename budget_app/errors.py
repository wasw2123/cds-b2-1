class BudgetAppError(Exception):
    def __init__(self, msg: str, hint: str = "") -> None:
        super().__init__(msg)
        self.msg = msg
        self.hint = hint
