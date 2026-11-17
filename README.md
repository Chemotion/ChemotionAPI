# ChemotionApi

A python api for [Chemotion](https://chemotion.net/). Chemotion is a Electronic Laboratory Notebook (ELN) developed at
the KIT is a web-based platform designed to help researchers manage and organize their experimental data in a secure and
efficient manner.

The ChemotionApi Python package is a wrapper for the RESTful API built on top of the Ruby on Rails
framework that allows users to interact with Chemotion ELN. The package provides a simple and intuitive
interface for creating, retrieving, updating, and deleting data stored in the ELN using Python. With
its RESTful architecture and comprehensive documentation, the ChemotionApi allows users to build custom applications and
workflows that leverage the ELN's capabilities and streamline their research processes.

## Documentation

Detaild documentation can be found [here](https://chemotionapi.readthedocs.io/en/main/)

## AI coding assistants

[skills/chemotion-api/](./skills/chemotion-api/SKILL.md) is a skill with the common workflows and a
signature reference (`references/api.md`). It also ships in the installed package, matching its
version, at `chemotion_api/skills/chemotion-api/` (find it with
`python -c "import chemotion_api, pathlib; print(pathlib.Path(chemotion_api.__file__).parent / 'skills')"`).

## Contributing

Contributions to ChemotionApi are welcome! If you have any bug reports, feature requests, or suggestions, please
open an issue on the GitHub repository. You can also submit
pull requests with your proposed changes.

## License

ChemotionApi is licensed under the GNU Affero General Public License v3 — see [LICENSE](./LICENSE).

**Let me know if there's anything else I can help you with!**
