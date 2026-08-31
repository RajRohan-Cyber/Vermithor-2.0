import os

from pathlib import Path


class FileActions:

    def open_path(
        self,
        path
    ):

        try:

            path = Path(
                os.path.expandvars(
                    os.path.expanduser(
                        path
                    )
                )
            ).resolve()


            os.startfile(
                str(path)
            )


            return (
                f"Opened {path}."
            )


        except Exception as error:

            return (
                f"I couldn't open "
                f"that path: {error}"
            )


    def list_directory(
        self,
        path="."
    ):

        try:

            path = Path(
                os.path.expandvars(
                    os.path.expanduser(
                        path
                    )
                )
            ).resolve()


            items = list(
                path.iterdir()
            )[:50]


            if not items:

                return (
                    "The directory "
                    "is empty."
                )


            return "\n".join(

                (
                    "[DIR] "
                    if item.is_dir()
                    else
                    "      "
                )
                +
                item.name

                for item in items

            )


        except Exception as error:

            return (
                f"I couldn't read "
                f"that directory: "
                f"{error}"
            )


    def create_folder(
        self,
        name
    ):

        try:

            path = Path(
                os.path.expandvars(
                    os.path.expanduser(
                        name
                    )
                )
            ).resolve()


            path.mkdir(
                parents=True,
                exist_ok=True
            )


            return (
                f"Folder '{path}' "
                "is ready."
            )


        except Exception as error:

            return (
                f"I couldn't create "
                f"the folder: {error}"
            )


    def file_exists(
        self,
        path
    ):

        path = Path(
            os.path.expandvars(
                os.path.expanduser(
                    path
                )
            )
        )


        if path.exists():

            return (
                f"Yes. '{path}' exists."
            )


        return (
            f"No. '{path}' "
            "does not exist."
        )