from driver import Driver
import tkinter as tk

if __name__ == "__main__":
    print("Running!")
    root = tk.Tk()
    root.title("Drone Demo")
    root.resizable(0,0)
    driver = Driver(root)
    root.mainloop()
