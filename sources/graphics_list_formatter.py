from enum import Enum
from typing import Dict, Tuple, List
from datetime import datetime

from pytz import timezone, utc

from manager_download import DownloadManager as DM
from manager_environment import EnvironmentManager as EM
from manager_github import GitHubManager as GHM
from manager_localization import LocalizationManager as LM


DAY_TIME_EMOJI = ["🌞", "🌆", "🌃", "🌙"]  # Emojis, representing different times of day.
DAY_TIME_NAMES = ["Morning", "Daytime", "Evening", "Night"]  # Localization identifiers for different times of day.
WEEK_DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]  # Localization identifiers for different days of week.


class Symbol(Enum):
    """
    Symbol version enum.
    Allows to retrieve symbols pairs by calling `Symbol.get_symbols(version)`.
    """

    VERSION_1 = "█", "░"
    VERSION_2 = "⣿", "⣀"
    VERSION_3 = "⬛", "⬜"

    @staticmethod
    def get_symbols(version: int) -> Tuple[str, str]:
        """
        Retrieves symbols pair for specified version.

        :param version: Required symbols version.
        :returns: Two strings for filled and empty symbol value in a tuple.
        """
        return Symbol[f"VERSION_{version}"].value


def make_graph(percent: float):
    """
    Make text progress bar.
    Length of the progress bar is 25 characters.

    :param percent: Completion percent of the progress bar.
    :return: The string progress bar representation.
    """
    done_block, empty_block = Symbol.get_symbols(EM.SYMBOL_VERSION)
    percent_quart = round(percent / 4)
    return f"{done_block * percent_quart}{empty_block * (25 - percent_quart)}"


def make_list(data: List = None, names: List[str] = None, texts: List[str] = None, percents: List[float] = None, top_num: int = 5, sort: bool = True) -> str:
    """
    Make list of text progress bars with supportive info.
    Each row has the following structure: [name of the measure] [quantity description (with words)] [progress bar] [total percentage].
    Name of the measure: up to 25 characters.
    Quantity description: how many _things_ were found, up to 20 characters.
    Progress bar: measure percentage, 25 characters.
    Total percentage: floating point percentage.

    :param data: list of dictionaries, each of them containing a measure (name, text and percent).
    :param names: list of names (names of measure), overloads data if defined.
    :param texts: list of texts (quantity descriptions), overloads data if defined.
    :param percents: list of percents (total percentages), overloads data if defined.
    :param top_num: how many measures to display, default: 5.
    :param sort: if measures should be sorted by total percentage, default: True.
    :returns: The string representation of the list.
    """
    if data is not None:
        names = [value for item in data for key, value in item.items() if key == "name"] if names is None else names
        texts = [value for item in data for key, value in item.items() if key == "text"] if texts is None else texts
        percents = [value for item in data for key, value in item.items() if key == "percent"] if percents is None else percents

    data = list(zip(names, texts, percents))
    top_data = sorted(data[:top_num], key=lambda record: record[2], reverse=True) if sort else data[:top_num]
    data_list = [f"{n[:25]}{' ' * (25 - len(n))}{t}{' ' * (20 - len(t))}{make_graph(p)}   {p:05.2f} % " for n, t, p in top_data]
    return "\n".join(data_list)


async def make_commit_day_time_list(time_zone: str) -> str:
    """
    Calculate commit-related info, how many commits were made, and at what time of day and day of week.

    :param time_zone: User time zone.
    :returns: string representation of statistics.
    """
    stats = str()

    result = await DM.get_remote_graphql("repos_contributed_to", username=GHM.USER.login)
    repos = [d for d in result["data"]["user"]["repositoriesContributedTo"]["nodes"] if d["isFork"] is False]

    day_times = [0] * 4  # 0 - 6, 6 - 12, 12 - 18, 18 - 24
    week_days = [0] * 7  # Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday

    for repository in repos:
        result = await DM.get_remote_graphql("repo_committed_dates", owner=repository["owner"]["login"], name=repository["name"], id=GHM.USER.node_id)
        if result["data"]["repository"] is None or result["data"]["repository"]["defaultBranchRef"] is None:
            continue

        committed_dates = result["data"]["repository"]["defaultBranchRef"]["target"]["history"]["nodes"]
        for committed_date in committed_dates:
            local_date = datetime.strptime(committed_date["committedDate"], "%Y-%m-%dT%H:%M:%SZ")
            date = local_date.replace(tzinfo=utc).astimezone(timezone(time_zone))

            day_times[date.hour // 6] += 1
            week_days[date.isoweekday() - 1] += 1

    sum_day = sum(day_times)
    sum_week = sum(week_days)
    day_times = day_times[1:] + day_times[:1]

    dt_names = [f"{DAY_TIME_EMOJI[i]} {LM.t(DAY_TIME_NAMES[i])}" for i in range(len(day_times))]
    dt_texts = [f"{day_time} commits" for day_time in day_times]
    dt_percents = [round((day_time / sum_day) * 100, 2) for day_time in day_times]
    title = LM.t("I am an Early") if sum(day_times[0:2]) >= sum(day_times[2:4]) else LM.t("I am a Night")
    stats += f"**{title}** \n\n```text\n{make_list(names=dt_names, texts=dt_texts, percents=dt_percents, top_num=7, sort=False)}\n```\n"

    if EM.SHOW_DAYS_OF_WEEK:
        wd_names = [LM.t(week_day) for week_day in WEEK_DAY_NAMES]
        wd_texts = [f"{week_day} commits" for week_day in week_days]
        wd_percents = [round((week_day / sum_week) * 100, 2) for week_day in week_days]
        title = LM.t("I am Most Productive on") % wd_names[wd_percents.index(max(wd_percents))]
        stats += f"📅 **{title}** \n\n```text\n{make_list(names=wd_names, texts=wd_texts, percents=wd_percents, top_num=7, sort=False)}\n```\n"

    return stats


def make_language_per_repo_list(repositories: Dict) -> str:
    """
    Calculate language-related info, how many repositories in what language user has.

    :param repositories: User repositories.
    :returns: string representation of statistics.
    """
    language_count = dict()
    repos_with_language = [repo for repo in repositories["data"]["user"]["repositories"]["nodes"] if repo["primaryLanguage"] is not None]
    for repo in repos_with_language:
        language = repo["primaryLanguage"]["name"]
        language_count[language] = language_count.get(language, {"count": 0})
        language_count[language]["count"] += 1

    names = list(language_count.keys())
    texts = [f"{language_count[lang]['count']} {'repo' if language_count[lang]['count'] == 1 else 'repos'}" for lang in names]
    percents = [round(language_count[lang]["count"] / len(repos_with_language) * 100, 2) for lang in names]

    top_language = max(list(language_count.keys()), key=lambda x: language_count[x]["count"])
    title = f"**{LM.t('I Mostly Code in') % top_language}** \n\n" if len(repos_with_language) > 0 else ""
    return f"{title}```text\n{make_list(names=names, texts=texts, percents=percents)}\n```\n\n"
