import os
import re

from module.base.filter import Filter
from module.campaign.run import CampaignRun
from module.config.config import TaskEnd
from module.config.utils import get_server_last_update
from module.logger import logger

STAGE_FILTER = Filter(regex=re.compile('^(.*?)$'), attr=('stage',))


class EventStage:
    def __init__(self, filename):
        self.filename = filename
        self.stage = 'unknown'
        if filename[-3:] == '.py':
            self.stage = filename[:-3]

    def __str__(self):
        return self.stage

    def __eq__(self, other):
        return str(self) == str(other)


class CampaignAB(CampaignRun):
    def run(self):
        stages = [EventStage(file) for file in os.listdir(f'./campaign/{self.config.Campaign_Event}')]
        logger.attr('Stage', [str(stage) for stage in stages])
        logger.attr('StageFilter', self.config.EventAb_StageFilter)
        STAGE_FILTER.load(self.config.EventAb_StageFilter)
        stages = STAGE_FILTER.apply(stages)
        logger.attr('Filter sort', ' > '.join([str(stage) for stage in stages]))

        if not stages:
            logger.warning('No stage satisfy current filter')
            self.config.Scheduler_Enable = False
            self.config.task_stop()

        logger.attr('LastStage', self.config.EventAb_LastStage)
        if get_server_last_update(self.config.Scheduler_ServerUpdate) >= self.config.Scheduler_NextRun:
            logger.info('Reset LastStage')
            self.config.EventAb_LastStage = 0
        if self.config.EventAb_LastStage in stages:
            stages = stages[stages.index(self.config.EventAb_LastStage) + 1:]

        # Run
        for stage in stages:
            stage = str(stage)
            try:
                super().run(name=stage, folder=self.config.Campaign_Event, total=1)
            except TaskEnd:
                # Catch task switch
                pass
            if self.run_count > 0:
                with self.config.multi_set():
                    self.config.EventAb_LastStage = stage
                    self.config.task_delay(minute=0)
            else:
                self.config.task_stop()
            if self.config.task_switched():
                self.config.task_stop()

        # Scheduler
        self.config.task_delay(server_update=True)
