## CLI Template for Indaleko

This folder provides a starter template for building a new CLI utility in the Indaleko project.

To create a new CLI tool:
1. Copy this entire `cli_template/` folder to a new directory under `tools/`, e.g. `tools/my_new_tool/`.
2. Rename `handler_mixin.py` and update the class name `TemplateHandlerMixin` to your tool's name.
3. Edit `cli.py`:
   - Update the import of `TemplateHandlerMixin` to your new mixin.
   - Set `RegistrationServiceName` and `FileServiceName` in the `IndalekoBaseCliDataModel` to descriptive values for your tool.
   - Implement or import your tool's core `run_<tool>` function and pass it as `Run` to `IndalekoCLIRunner`.
4. Adjust default arguments and parameters by overriding the hook methods in your handler mixin.
5. Run your new CLI:
    ```bash
    python tools/my_new_tool/cli.py --help
    ```

This template uses the shared `IndalekoCLIRunner` framework for consistent argument parsing, configuration loading,
logging setup, performance recording, and cleanup.  Customize only the mixin and core logic—boilerplate is handled
for you.
