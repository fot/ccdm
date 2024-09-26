"MSID Plotter Tool"

from os import system
from components.plot import generate_plot
from components.user_inputs import get_user_inputs, UserVariables
from components.misc import user_menu, generate_html_output, cleanup


def main():
    "Main execution"
    user_vars = UserVariables()
    get_user_inputs(user_vars, "all")

    while True:
        try:
            plot = generate_plot(user_vars)
            generate_html_output(user_vars, plot)
            if input("""\nTo Restart Tool, Input "1": """) != "1":
                break
            get_user_inputs(user_vars, "all")
        except KeyboardInterrupt: # handle canceling plot generation
            system("clear")
            print("Interrupted plot generation....\n")

            choice = user_menu()
            if choice == "1":
                get_user_inputs(user_vars, "all")
            elif choice == "2":
                get_user_inputs(user_vars, "dates")
            elif choice == "3":
                get_user_inputs(user_vars, "MSIDs")
            elif choice == "4":
                get_user_inputs(user_vars, "data source")
            else: break


main()
cleanup()
