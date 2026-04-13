[Skip to content](https://www.nngroup.com/articles/empty-state-interface-design/#main)

NEW \| NN/G Self-Paced Training — Expert depth. Your schedule.


[Find Your Course](https://www.nngroup.com/contents/self-paced-courses/?utm_source=website&utm_medium=homepage-banner&utm_campaign=push1&utm_content=tier1-existing)

[Nielsen Norman GroupNielsen Norman Group](https://www.nngroup.com/)

- UX Training & Courses
   - ### Live Online

    - [All Live Online Courses](https://www.nngroup.com/courses/)
    - [Upcoming Live Online Training](https://www.nngroup.com/training/live-courses/)
    - [UX Certification](https://www.nngroup.com/ux-certification/)
    - [Private Team Training](https://www.nngroup.com/team-training/)
    - [Bulk Discounts](https://www.nngroup.com/training/bulk-discounts/)
  - ### Self-Paced

    - [Self-Paced Courses](https://www.nngroup.com/contents/self-paced-courses/)
- Articles & Resources
   - [Articles & Videos](https://www.nngroup.com/articles/)
  - [Reports & Books](https://www.nngroup.com/reports/)
  - [The NN/G UX Podcast](https://podcasters.spotify.com/pod/show/nngroup)
- Consulting
   - [All Consulting Services](https://www.nngroup.com/consulting/)
  - [Customized Research](https://www.nngroup.com/consulting/user-research/)
  - [Expert Review](https://www.nngroup.com/consulting/expert-review/)
  - [Intensive Applied Workshops](https://www.nngroup.com/consulting/applied-workshops/)
  - [Keynote Speaking](https://www.nngroup.com/consulting/keynote-speaking/)
  - [User Testing](https://www.nngroup.com/consulting/user-testing/)
  - [UX Maturity Assessment](https://www.nngroup.com/consulting/ux-maturity-assessment/)
- About Us
   - [About NNGroup](https://www.nngroup.com/about/)
  - [People](https://www.nngroup.com/people/)
  - [Clients](https://www.nngroup.com/about/about-client-list/)
  - [News & Careers](https://www.nngroup.com/news/)
  - [FAQs](https://www.nngroup.com/faqs/)
  - [Contact Us](https://www.nngroup.com/about/contact/)

Search

When autocomplete results are available use up and down arrows to review and enter to select. Touch device users, explore by touch or with swipe gestures.

[0](https://www.nngroup.com/products/basket/)

[Log In](https://www.nngroup.com/login/?next=%2Farticles%2Fempty-state-interface-design%2F)

6

# Designing Empty States in Complex Applications: 3 Guidelines

Kate Kaplan

![](https://media.nngroup.com/media/people/photos/2023-04-portraits-katek-3.jpg.256x256_q75_autocrop_crop-smart_upscale.jpg)

[Kate Kaplan](https://www.nngroup.com/articles/author/kate-kaplan/)

September 19, 2021

2021-09-19

[Share](https://www.nngroup.com/articles/empty-state-interface-design/#)

- [Email article](mailto:?subject=NN/g%20Article:%20Designing%20Empty%20States%20in%20Complex%20Applications:%203%20Guidelines&body=https://www.nngroup.com/articles/empty-state-interface-design/)
- [Share on LinkedIn](http://www.linkedin.com/shareArticle?mini=true&url=http://www.nngroup.com/articles/empty-state-interface-design/&title=Designing%20Empty%20States%20in%20Complex%20Applications:%203%20Guidelines&source=Nielsen%20Norman%20Group)
- [Share on Twitter](https://twitter.com/intent/tweet?url=http://www.nngroup.com/articles/empty-state-interface-design/&text=Designing%20Empty%20States%20in%20Complex%20Applications:%203%20Guidelines&via=nngroup)

Summary:
Empty states provide opportunities for designers to communicate system status, increase learnability of the system, and deliver direct pathways for key tasks. This article provides guidance for designing empty-state dialogues for content-less containers.


At times, users will encounter empty states within an application: containers, screens, or panels for which content does not yet exist or otherwise cannot be displayed.

Especially in [complex applications](https://www.nngroup.com/articles/complex-application-design-framework/) that have not been fully configured by the user, empty states are quite common during [onboarding](https://www.nngroup.com/videos/onboarding-new-users/) and initial usage. Some typical scenarios when users might encounter empty states within an application are:

- When a user has not designated any items as _favorites_ or has not opened any files yet, containers meant to display lists of favorited or recently viewed items will be empty.
- When an application supports [alerts](https://www.nngroup.com/articles/indicators-validations-notifications/), but a user has not yet configured any alerts, there may be an empty pane or dialogue where those alerts will eventually appear.
- When an application is composed of various workspaces or [dashboards](https://www.nngroup.com/articles/dashboards-preattentive/), but a user has not added content to those areas, those pages or screens will be empty.
- [Search results lists when nothing is found](https://www.nngroup.com/articles/search-no-results-serp/), as well as other cases where a command creates empty output.

The default of an empty space is to simply remain empty: Display no content to the user until the space has been configured or personalized. While this approach may save development time (or even be an intentional decision during an early beta design of a product where other features must be initially prioritized), it ultimately creates confusion and decreases user confidence — and misses a goldmine of opportunities for increasing the [usability](https://www.nngroup.com/articles/usability-101-introduction-to-usability/) and the [learnability](https://www.nngroup.com/articles/measure-learnability/) of the application, as well as the [discoverability](https://www.nngroup.com/articles/navigation-ia-tests/) of key features.

Empty states that are intentionally designed — not left as an afterthought — can be used to:

- Communicate system status to the user
- Help users discover unused features and increase learnability of the application
- Provide direct pathways for getting started with key tasks

## In This Article:

[Use Empty States to Communicate System Status](https://www.nngroup.com/articles/empty-state-interface-design/#toc-use-empty-states-to-communicate-system-status-1)

- [Use Empty States to Communicate System Status](https://www.nngroup.com/articles/empty-state-interface-design/#toc-use-empty-states-to-communicate-system-status-1)
- [Use Empty States to Provide Learning Cues](https://www.nngroup.com/articles/empty-state-interface-design/#toc-use-empty-states-to-provide-learning-cues-2)
- [Use Empty States to Provide Direct Pathways for Key Tasks](https://www.nngroup.com/articles/empty-state-interface-design/#toc-use-empty-states-to-provide-direct-pathways-for-key-tasks-3)
- [Conclusion](https://www.nngroup.com/articles/empty-state-interface-design/#toc-conclusion-4)

## Use Empty States to Communicate System Status

Totally empty states cause confusion about how and whether the system is working. When users encounter an empty panel or screen in an interface after attempting to filter, query or display specific content, they’re likely left wondering a myriad of questions: Is the system finished processing the request? Is content still loading? Did an error occur? Did I set the wrong filters or parameters?

As an example, consider the dialogue for displaying log details below. When a user specifies and applies a date range for which there are no logs, the table in the dialogue — logically — does not display any log details. However, because there is no system feedback provided, the user cannot know whether there truly are no details to display,  whether an error has occurred, or whether the system is still processing the request. Users are likely to waste time refreshing the query several times before feeling confident enough to move on.

![Panel for a table to display log items within a certain date range. Panel is empty and contains to items and no system message.](https://media.nngroup.com/media/editor/2021/09/15/empty_state_without_system_message.jpeg)_This dialogue lacks appropriate feedback: It is unclear whether there are no details to display in the table or the system is still working on gathering and displaying the details._

A brief system message within the content area at completion of the process (e.g., “There are no records to display for the selected date range”) would be a simple yet effective way to increase the [visibility of system status](https://www.nngroup.com/articles/visibility-system-status/) and, therefore, user confidence in the results.

![Panel for a table to display log items within a certain date range. Panel contains a system message stating “There are no records to display for the selected date range.”](https://media.nngroup.com/media/editor/2021/09/15/empty_state_with_system_message.jpeg)_A simple message (There are no records to display for the selected date range) communicates the state of the system and increases user confidence._

A worse, yet equally common scenario, especially in applications with high information density and lengthy processing times, is when the system defaults to a _misleading_ system-status message: declaring that there are no items to display, only to replace it with content after the process is completed.

For example, when loading content in the employee-management software below, users encounter an empty-state container with the system-status message _No_ _records_. This information would be highly useful if, in fact, there were no records. However, after a few seconds of waiting, the system replaces the inaccurate system-status message with the requested items.

![Left image shows a screen meant to display email templates with message "No records." Right image shows the screen a few seconds later, with multiple email template items populated.](https://media.nngroup.com/media/editor/2021/09/15/empty_state_ui_inaccurate_system_message.jpeg)_Upon entering a new screen, users initially encounter an inaccurate system-status message No records (left). After several seconds, as the system finishes loading content, the message is replaced with a list of relevant items (right)._

Inaccurate system-status messages for empty states are particularly harmful. In the best-case scenario, users wait out the process and discover the relevant content but develop a severe distrust of and distaste for the application. In the worst-case scenario, trigger-happy users (that is, most users) never see the relevant content and cannot complete their work.

## Use Empty States to Provide Learning Cues

In-context learning cues displayed when the user has started a task help users understand how to use an application or system in real time, as they explore the system. In most cases, this approach is generally more successful than forced tutorials shown to the user at initial use. That’s because in-context help can often be applied right away and is thus more memorable — users have little time to establish associations between lengthy onboarding content and the actual interface.

Empty states present an opportunity to provide contextual help relevant to the user’s task. These help messages are sometimes called [pull revelations](https://www.nngroup.com/articles/help-and-documentation/) because they show up only when the user interacts with the corresponding UI element and they are not “pushed” in any obtrusive or interruptive way.

For example, consider the _Alerts_ panel below from an enterprise resource-planning (ERP) application. When the _Alerts_ panel is populated with alerts, it is fairly obvious how one might engage with the content. (This state of the panel is probably how this element was mocked up and tested.) However, when the _Alerts_ panel is empty, it presents the issues previously discussed: Users may wonder whether an error has occurred or whether they have accurately created parameters necessary to trigger alerts. (As in the earlier example, a brief system-status message stating that there are no alerts would be useful here.)

Furthermore, though, this totally empty state of the _Alerts_ panel misses an opportunity to educate the user about the alerts function. A brief dialogue could provide information about what alerts are and how to get started using them.

![Left screen shows an alerts panel populated with personalized alerts. Right panel shows the same alerts panel when no alerts are triggered.](https://media.nngroup.com/media/editor/2021/09/15/alerts_panel_empty_state_ui_design.png)_When there are active alerts (left), it is easy enough to understand how to dismiss and view details for alerts. When no alerts exist or have been created (right), the panel reverts to a totally empty state, missing an opportunity to provide contextual help to the user._

In contrast, DataDog, a data-monitoring application, makes use of contextual help content within the empty state. When the user has not starred any items to create a list of favorites, the would-be content area displays the message _Star your favorites to list them here_.

![Side navigation menu contains the message, "Star your favorites to list them here" when no favorites have been added](https://media.nngroup.com/media/editor/2021/09/15/star_favorites_dialog_message_empty_state_interface.jpg)_DataDog: When the users have not selected any favorites, the message_ Star your favorites to list them here _, shown in the empty-state container, teaches users about the favoriting functionality and explains how the empty area could be used._

In a similar example, when no items have been recently viewed in Microsoft Power BI, the empty-state screen contains a brief system message describing how content is added there.

![](https://media.nngroup.com/media/editor/2021/09/15/powerbi_empty_state_message.jpg)_Microsoft Power BI: The empty-state container for inexistent recent items explains how content gets added to this area._

## Use Empty States to Provide Direct Pathways for Key Tasks

In addition to alerting users of system status and increasing system learnability with pull revelations, empty states can also be used to provide direct pathways for getting users started with key tasks or completing steps related to their current workflow.

For example, in one application-development software, the following system-status message _No Records; Send a request to view details in the workspace_ was encountered in an empty state when no records were able to be displayed during a task. While this message does provide contextual information about _what_ the user could do to view these records (i.e., it says to _Send_ a _request_ _to view details in the workspace_), it doesn’t tell the user _how_ to accomplish that task, or where to go in the system to find the necessary functionality.

![](https://media.nngroup.com/media/editor/2021/09/15/no_records_send_a_request_dialog.png)_This system-status message within an empty state provides contextual help about what the user could do to view records, but it doesn’t tell the user how to accomplish the task._

A better approach is to provide brief yet explicit instructions or, better yet, link directly to the steps that need to be taken to complete tasks associated with populating the empty state. (Here, the text _Send a request_ might directly link to a message center or launch a message dialogue.)

For example, the application below provides a direct link within the empty state — a button labeled _Create_ which allows users to create alerts. For users who may need more information to understand why alerts are useful and how to use them, a _Learn more_ link item also leads directly to associated documentation.

![](https://media.nngroup.com/media/editor/2021/09/15/no_alerts_panel.jpg)_The empty-state alerts panel links to additional relevant documentation and provides a button to begin creating alerts from directly within the empty state._

This type of empty-state design has useful implications for users getting started with complex application features, as well. For example, when users have yet to add log data to their accounts within Loggly, a cloud-based log-management application, the empty state contains 2 direct pathways into the workflow: adding external log sources or populating demo data into the application to use for safe exploration.

![](https://media.nngroup.com/media/editor/2021/09/15/loggly_empty_state_message_screen.jpg)_Loggly: An empty-state screen provides 2 direct pathways for getting started: adding log sources or exploring with demo data._

## Conclusion

Don’t let empty-state design be an afterthought within your application. Intentionally designed empty states can help increase user confidence, improve system learnability, and help users get started with key tasks.

To summarize a few main points:

- Do not default to totally empty states. This approach creates confusion for users, who may be left wondering if the system is still loading information or if errors have occurred.
- When content does not yet exist for a screen, page, or panel, use the empty state to provide help cues. Tell the user what could be displayed, and how to populate the area with that content.
- Provide direct pathways (i.e., links) to getting started with key tasks related to populating the empty state.
- When a process is running, use [progress indicators](https://www.nngroup.com/articles/progress-indicators/) to increase visibility of system status.
- If there is no relevant data to display after a process has completed, use the empty space to provide a system-status message in the empty space that briefly states that no content is available.

Interaction Design,complex applications,Design Patterns

## Related Topics

- Interaction Design [Interaction Design](https://www.nngroup.com/topic/interaction-design/)
- [Design Patterns](https://www.nngroup.com/topic/design-patterns/)

## Learn More:

- [![](https://media.nngroup.com/media/videos/thumbnails/Button_States_Thumbnail.jpg.650x364_q75_autocrop_crop-smart_upscale.jpg)\\
\\
Button States 101\\
\\
\\
Kelley Gordon\\
\\
\\
·\\
3 min](https://www.nngroup.com/videos/button-states-101/?lm=empty-state-interface-design&pt=article)

- [![](https://media.nngroup.com/media/videos/thumbnails/3_Ways_to_Test_Your_Survey_Thumbnail.jpg.650x364_q75_autocrop_crop-smart_upscale.jpg)\\
\\
3 Ways to Test Your Survey\\
\\
\\
Maddie Brown\\
\\
\\
·\\
3 min](https://www.nngroup.com/videos/3-ways-to-test-surveys/?lm=empty-state-interface-design&pt=article)

- [![](https://media.nngroup.com/media/videos/thumbnails/UX_vs_UI_Thumbnail.jpg.650x364_q75_autocrop_crop-smart_upscale.jpg)\\
\\
UX vs. UI\\
\\
\\
Sarah Gibbons\\
\\
\\
·\\
3 min](https://www.nngroup.com/videos/ux-vs-ui/?lm=empty-state-interface-design&pt=article)


## Related Articles:

- [Designing for Long Waits and Interruptions: Mitigating Breaks in Workflow in Complex Application Design\\
\\
Kate Kaplan\\
\\
\\
·\\
9 min](https://www.nngroup.com/articles/designing-for-waits-and-interruptions/?lm=empty-state-interface-design&pt=article)
- [8 Design Guidelines for Complex Applications\\
\\
Kate Kaplan\\
\\
\\
·\\
8 min](https://www.nngroup.com/articles/complex-application-design/?lm=empty-state-interface-design&pt=article)
- [Drag–and–Drop: How to Design for Ease of Use\\
\\
Page Laubheimer\\
\\
\\
·\\
11 min](https://www.nngroup.com/articles/drag-drop/?lm=empty-state-interface-design&pt=article)
- [10 Usability Heuristics Applied to Complex Applications\\
\\
Kate Kaplan\\
\\
\\
·\\
12 min](https://www.nngroup.com/articles/usability-heuristics-complex-applications/?lm=empty-state-interface-design&pt=article)
- [Design-Pattern Guidelines: Study Guide\\
\\
Samhita Tankala and Alita Kendrick\\
\\
\\
·\\
6 min](https://www.nngroup.com/articles/design-pattern-guidelines/?lm=empty-state-interface-design&pt=article)
- [Split Buttons: Definition\\
\\
Page Laubheimer\\
\\
\\
·\\
7 min](https://www.nngroup.com/articles/split-buttons/?lm=empty-state-interface-design&pt=article)

## Never miss an update

Get weekly UX articles, videos, upcoming courses, and job openings straight to your inbox with our newsletter.

EmailSubscribe

- ### Courses

  - [Live Online Courses](https://www.nngroup.com/courses/)
  - [Self-Paced Courses](https://www.nngroup.com/contents/self-paced-courses/)
- ### Consulting

  - [Intensive Applied Workshops](https://www.nngroup.com/consulting/applied-workshops/)
  - [Customized Research](https://www.nngroup.com/consulting/user-research/)
  - [Expert Review](https://www.nngroup.com/consulting/expert-review/)
  - [Keynote Speaking](https://www.nngroup.com/consulting/keynote-speaking/)
  - [User Testing](https://www.nngroup.com/consulting/user-testing/)
  - [UX Maturity Assessment](https://www.nngroup.com/consulting/ux-maturity-assessment/)
- ### Help

  - [Terms & Conditions](https://www.nngroup.com/terms-and-conditions/)
  - [Privacy Policy](https://www.nngroup.com/privacy-policy/)
  - [Live Course Tech Support](https://www.nngroup.com/virtual-help)
  - [FAQs](https://www.nngroup.com/faqs/)
- ### Company

  - [About NNGroup](https://www.nngroup.com/about/)
  - [People](https://www.nngroup.com/people/)
  - [News & Careers](https://www.nngroup.com/news/)
  - [Contact Us](https://www.nngroup.com/about/contact/)

Copyright © 1998-2026 Nielsen Norman Group, All Rights Reserved.


- Cookie Preferences
- [Cookie Declaration](https://www.nngroup.com/cookie-declaration/)

## Follow Us

- [Youtube](https://www.youtube.com/channel/UC2oCugzU6W8-h95W7eBTUEg)
- [LinkedIn](https://www.linkedin.com/company/nielsen-norman-group)
- [Instagram](https://www.instagram.com/nngux)
- [Threads](https://www.threads.com/@nngux)
- [Bluesky](https://bsky.app/profile/nngroupux.bsky.social)
- [X](https://x.com/nngroup)
- [Facebook](https://www.facebook.com/nngux)
- [Spotify](https://podcasters.spotify.com/pod/show/nngroup)

 Back to Top