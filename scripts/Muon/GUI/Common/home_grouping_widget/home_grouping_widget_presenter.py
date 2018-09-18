from __future__ import (absolute_import, division, print_function)

from Muon.GUI.Common.home_tab.home_tab_presenter import HomeTabSubWidget


class HomeGroupingWidgetPresenter(HomeTabSubWidget):

    def __init__(self, view, model):
        self._view = view
        self._model = model

        self._view.on_grouppair_selection_changed(self.handle_grouppair_selector_changed)

        self._view.on_alpha_changed(self.handle_user_changes_alpha)

        self._view.on_summed_periods_changed(self.handle_periods_changed)
        self._view.on_subtracted_periods_changed(self.handle_periods_changed)

    def show(self):
        self._view.show()

    def handle_user_changes_alpha(self):
        alpha = self._view.get_current_alpha()
        pair_name = self._view.get_currently_selected_group_pair()
        self._model.update_pair_alpha(pair_name, alpha)

    def update_group_pair_list(self):
        group_names = self._model.get_group_names()
        pair_names = self._model.get_pair_names()
        self._view.populate_group_pair_selector(group_names, pair_names)

    def hide_multiperiod_widget_if_data_single_period(self):
        if self._model.is_data_multi_period():
            self._view.multi_period_widget_hidden(False)
        else:
            self._view.multi_period_widget_hidden(True)

    def handle_grouppair_selector_changed(self):
        name = self._view.get_selected_group_or_pair_name()
        if self._model.is_group(name):
            self._view.alpha_hidden(True)
        elif self._model.is_pair(name):
            self._view.alpha_hidden(False)
            alpha = self._model.get_alpha(name)
            self._view.set_current_alpha(alpha)
        else:
            self._view.alpha_hidden(True)

    def update_view_from_model(self):
        self.update_group_pair_list()
        self.hide_multiperiod_widget_if_data_single_period()

        n_periods = self._model.number_of_periods()
        self._view.set_period_number_in_period_label(n_periods)

    def string_to_list(self, text):
        if text == "":
            return []
        return [int(i) for i in text.split(",")]

    def update_period_edits(self):
        summed_periods = self._model.get_summed_periods()
        subtracted_periods = self._model.get_subtracted_periods()

        self._view.set_summed_periods(",".join([str(p) for p in summed_periods]))
        self._view.set_subtracted_periods(",".join([str(p) for p in subtracted_periods]))

    def handle_periods_changed(self):
        summed = self.string_to_list(self._view.get_summed_periods())
        subtracted = self.string_to_list(self._view.get_subtracted_periods())

        subtracted = [i for i in subtracted if i not in summed]

        n_periods = self._model.number_of_periods()
        bad_periods = [p for p in summed if (p > n_periods) or p == 0] + [p for p in subtracted if
                                                                          (p > n_periods) or p == 0]
        if len(bad_periods) > 0:
            self._view.warning_popup("The following periods are invalid : " + ",".join([str(p) for p in bad_periods]))

        summed = [p for p in summed if (p <= n_periods) and p > 0]
        subtracted = [p for p in subtracted if (p <= n_periods) and p > 0]

        self._model.update_summed_periods(summed)
        self._model.update_subtracted_periods(subtracted)

        self.update_period_edits()