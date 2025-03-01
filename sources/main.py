"""
Readme Development Metrics With waka time progress
"""
from asyncio import run
from datetime import datetime
from urllib.parse import quote

from humanize import intword, naturalsize, intcomma, precisedelta

from manager_download import init_download_manager, DownloadManager as DM
from manager_environment import EnvironmentManager as EM
from manager_github import init_github_manager, GitHubManager as GHM
from manager_localization import init_localization_manager, LocalizationManager as LM
from graphics_chart_drawer import create_loc_graph, GRAPH_PATH
from yearly_commit_calculator import calculate_yearly_commit_data
from graphics_list_formatter import make_list, make_commit_day_time_list, make_language_per_repo_list


async def get_waka_time_stats() -> str:
    """
    Collects user info from wakatime.
    Info includes most common commit time, timezone, language, editors, projects and OSs.

    :returns: String representation of the info.
    """
    stats = str()

    data = await DM.get_remote_json("waka_latest")
    if EM.SHOW_COMMIT:
        stats += f"{await make_commit_day_time_list(data['data']['timezone'])}\n\n"

    if EM.SHOW_TIMEZONE or EM.SHOW_LANGUAGE or EM.SHOW_EDITORS or EM.SHOW_PROJECTS or EM.SHOW_OS:
        no_activity = LM.t("No Activity Tracked This Week")
        stats += f"📊 **{LM.t('This Week I Spend My Time On')}** \n\n```text\n"

        if EM.SHOW_TIMEZONE:
            time_zone = data["data"]["timezone"]
            stats += f"🕑︎ {LM.t('Timezone')}: {time_zone}\n\n"

        if EM.SHOW_LANGUAGE:
            lang_list = no_activity if len(data["data"]["languages"]) == 0 else make_list(data["data"]["languages"])
            stats += f"💬 {LM.t('Languages')}: \n{lang_list}\n\n"

        if EM.SHOW_EDITORS:
            edit_list = no_activity if len(data["data"]["editors"]) == 0 else make_list(data["data"]["editors"])
            stats += f"🔥 {LM.t('Editors')}: \n{edit_list}\n\n"

        if EM.SHOW_PROJECTS:
            project_list = no_activity if len(data["data"]["projects"]) == 0 else make_list(data["data"]["projects"])
            stats += f"🐱‍💻 {LM.t('Projects')}: \n{project_list}\n\n"

        if EM.SHOW_OS:
            os_list = no_activity if len(data["data"]["operating_systems"]) == 0 else make_list(data["data"]["operating_systems"])
            stats += f"💻 {LM.t('operating system')}: \n{os_list}\n\n"

        stats = f"{stats[:-1]}```\n\n"

    return stats


async def get_short_github_info() -> str:
    """
    Collects user info from GitHub public profile.
    The stats include: disk usage, contributions number, whether the user has opted to hire, public and private repositories number.

    :returns: String representation of the info.
    """
    stats = f"**🐱 {LM.t('My GitHub Data')}** \n\n"

    if GHM.USER.disk_usage is None:
        disk_usage = LM.t("Used in GitHub's Storage") % "?"
        print("Please add new github personal access token with user permission!")
    else:
        disk_usage = LM.t("Used in GitHub's Storage") % naturalsize(GHM.USER.disk_usage)
    stats += f"> 📦 {disk_usage} \n > \n"

    data = await DM.get_remote_json("github_stats")
    if len(data["years"]) > 0:
        contributions = LM.t("Contributions in the year") % (intcomma(data["years"][0]["total"]), data["years"][0]["year"])
        stats += f"> 🏆 {contributions}\n > \n"

    opted_to_hire = GHM.USER.hireable
    if opted_to_hire:
        stats += f"> 💼 {LM.t('Opted to Hire')}\n > \n"
    else:
        stats += f"> 🚫 {LM.t('Not Opted to Hire')}\n > \n"

    public_repo = GHM.USER.public_repos
    if public_repo != 1:
        stats += f"> 📜 {LM.t('public repositories') % public_repo} \n > \n"
    else:
        stats += f"> 📜 {LM.t('public repository') % public_repo} \n > \n"

    private_repo = GHM.USER.owned_private_repos if GHM.USER.owned_private_repos is not None else 0
    if public_repo != 1:
        stats += f"> 🔑 {LM.t('private repositories') % private_repo} \n > \n"
    else:
        stats += f"> 🔑 {LM.t('private repository') % private_repo} \n > \n"

    return stats


async def get_stats() -> str:
    """
    Creates new README.md content from all the acquired statistics from all places.
    The readme includes data from wakatime, contributed lines of code number, GitHub profile info and last updated date.

    :returns: String representation of README.md contents.
    """
    stats = str()
    repositories = await DM.get_remote_graphql("user_repository_list", username=GHM.USER.login, id=GHM.USER.node_id)

    if EM.SHOW_LINES_OF_CODE or EM.SHOW_LOC_CHART:
        yearly_data = await calculate_yearly_commit_data(repositories)
    else:
        yearly_data = (None, dict())

    if EM.SHOW_TOTAL_CODE_TIME:
        data = await DM.get_remote_json("waka_all")
        stats += f"![Code Time](http://img.shields.io/badge/{quote('Code Time')}-{quote(str(data['data']['text']))}-blue)\n\n"

    if EM.SHOW_PROFILE_VIEWS:
        data = GHM.REPO.get_views_traffic(per="week")
        stats += f"![Profile Views](http://img.shields.io/badge/{quote(LM.t('Profile Views'))}-{data['count']}-blue)\n\n"

    if EM.SHOW_LINES_OF_CODE:
        total_loc = sum([yearly_data[y][q][d] for y in yearly_data.keys() for q in yearly_data[y].keys() for d in yearly_data[y][q].keys()])
        data = f"{intword(total_loc)} {LM.t('Lines of code')}"
        stats += f"![Lines of code](https://img.shields.io/badge/{quote(LM.t('From Hello World I have written'))}-{quote(data)}-blue)\n\n"

    if EM.SHOW_SHORT_INFO:
        stats += await get_short_github_info()

    stats += await get_waka_time_stats()

    if EM.SHOW_LANGUAGE_PER_REPO:
        stats += f"{make_language_per_repo_list(repositories)}\n\n"

    if EM.SHOW_LOC_CHART:
        await create_loc_graph(yearly_data, GRAPH_PATH)
        GHM.update_chart(GRAPH_PATH)
        chart_path = f"{GHM.USER.login}/{GHM.USER.login}/{GHM.branch()}/{GRAPH_PATH}"
        stats += f"**{LM.t('Timeline')}**\n\n![Lines of Code chart](https://raw.githubusercontent.com/{chart_path})\n\n"

    if EM.SHOW_UPDATED_DATE:
        stats += f"\n Last Updated on {datetime.now().strftime(EM.UPDATED_DATE_FORMAT)} UTC"

    return stats


async def main():
    """
    Application main function.
    Initializes all managers, collects user info and updates README.md if necessary.
    """
    init_github_manager()
    await init_download_manager()
    init_localization_manager()

    if GHM.update_readme(await get_stats()):
        print("Readme updated!")
    await DM.close_remote_resources()


if __name__ == "__main__":
    start_time = datetime.now()
    run(main())
    run_delta = datetime.now() - start_time
    print(f"Program processed in {precisedelta(run_delta, minimum_unit='microseconds')}.")
