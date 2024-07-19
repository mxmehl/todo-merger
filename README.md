# ToDo Merger

Get an overview of all issues assigned to you on GitHub and one or more GitLab
instances.

Very early stage, contributions and ideas are welcome!


## Installation

### Install and run via pipx (Recommended)

[pipx](https://pypa.github.io/pipx/) makes installing and running Python programs easier and avoid conflicts with other packages. Install it with

```sh
pip3 install pipx
```

The following one-liner both installs and runs this program from [PyPI](https://pypi.org/project/todo-merger/):

```sh
pipx run todo-merger
```

If you want to be able to use todo-merger without prepending it with `pipx run` every time, install it globally like so:

```sh
pipx install todo-merger
```

todo-merger will then be available in `~/.local/bin`, which must be added to your `$PATH`. On Windows, the required path for your environment may look like `%USERPROFILE%\AppData\Roaming\Python\Python310\Scripts`, depending on the Python version you have installed.

To upgrade todo-merger to the newest available version, run this command:

```sh
pipx upgrade todo-merger
```

### Other installation methods

You may also use pure `pip` or `poetry` to install this package.


## Usage

Run `todo-merger`. This will run the application. You can interact with it using your browser on http://localhost:8636.


## Configuration

Upon start, the program will create a new empty configuration file. You will probably run into an error because no login data is present. From the error messages, you can find the config file in which you will have to add your data.

This will surely be improved in the next versions.


## License

The main license of this project is the GNU General Public License 3.0, no later version (`GPL-3.0-only`), Copyright Max Mehl.

There are also parts from third parties under different licenses, e.g. Pico CSS (MIT) and snippets from DB Systel (Apache-2.0). Thank you!
