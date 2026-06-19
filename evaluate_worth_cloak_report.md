# evaluate_worth_cloak 评估报告

- **时间**: 2026-06-19 07:58:28
- **总处理**: 288
- **模式**: --apply (已写入数据库)

| 结果 | 数量 |
|------|------|
| ❌ worth=0 (硬障碍) | 13 |
| ✅ worth=1 (blog_comment 确认有表单) | 3 |
| ⚠️ 有表单-仅报告 (非 blog_comment) | 40 |
| 🔍 保留 NULL (待复查) | 232 |

## ❌ 硬障碍 → worth=0

| ID | 类型 | URL | 原因 |
|----|------|-----|------|
| 68 | form | http://www.5118.link/article/22.html | DNS resolution failed |
| 70 | form | https://700.tools/add | DNS resolution failed |
| 99 | form | https://aiwaytools.com/%e7%bd%91%e5%9d%80%e6%8f%90%e4%ba%a4/ | DNS resolution failed |
| 102 | form | https://aidude.pro/submit-your-tool | DNS resolution failed |
| 107 | form | https://allthingsai.com | DNS resolution failed |
| 116 | form | https://chatgptdemo.pro/submit-tool/ | DNS resolution failed |
| 120 | form | https://digiprotoolz.com/contact-us/ | DNS resolution failed |
| 149 | form | https://www.launching.today/ | DNS resolution failed |
| 202 | form | https://www.unloc.tools/submit-tool | DNS resolution failed |
| 208 | form | https://www.worldweb-directory.com/add.php | DNS resolution failed |
| 233 | form | https://nav.6aiq.com/contribute | DNS resolution failed |
| 236 | form | https://www.dianshangdaohang.cn/shoulu/ | DNS resolution failed |
| 282 | pending | https://www.findatool.io/add-a-tool | SSL error |

## ✅ 确认有表单 → worth=1

| ID | 类型 | URL | 原因 |
|----|------|-----|------|
| 389 | blog_comment | https://www.simonsaysstampblog.com/blog/amore-laurafadora-3/comment-page-1/ | OK |
| 410 | blog_comment | https://www.craftberrybush.com/2025/01/heart-shaped-flower-arrangement-for-valentines-day.html | OK |
| 490 | blog_comment | https://www.craftberrybush.com/2017/08/watercolor-lessons-and-free-printable.html | OK |

## ⚠️ 有表单 (仅报告, 未标记)

| ID | 类型 | URL | 原因 |
|----|------|-----|------|
| 17 | directory | https://www.uneed.best/submit-a-tool | OK |
| 18 | directory | https://www.toolify.ai/submit | OK |
| 19 | form | https://theresanaiforthat.com/launch/ | OK |
| 21 | directory | https://dofollow.tools/submit | OK |
| 27 | directory | https://toolverto.com/zh-cn/submit-tool | OK |
| 42 | directory | https://aivalley.ai/submit-prompts/ | OK |
| 46 | directory | https://aidir.wiki/submit-tool | OK |
| 63 | form | https://www.01webdirectory.com/frmpresubmit.aspx | OK |
| 69 | form | https://www.63243.com/about/add.html | OK |
| 106 | form | https://www.allstatesusadirectory.com/submit.php | OK |
| 113 | form | https://bufferapps.com/beta-listing/new | OK |
| 115 | form | https://changelog.com/news/submit | OK |
| 143 | form | https://www.insidr.ai/submit-tools/ | OK |
| 145 | form | https://www.jayde.com/submit.html | OK |
| 150 | form | https://www.marketinginternetdirectory.com/submit.php | OK |
| 151 | form | https://mergeek.com/publish_project | OK |
| 155 | form | https://www.offpagesavvy.com/submit-your-site/ | OK |
| 156 | form | https://www.ontoplist.com/join/ | OK |
| 159 | form | https://poweredbyai.app/submit-tool | OK |
| 161 | form | https://www.prolinkdirectory.com/submit.php | OK |
| 163 | form | https://www.qualityinternetdirectory.com/submit.php | OK |
| 166 | form | https://www.sitepromotiondirectory.com/submit.php | OK |
| 173 | form | https://startupcollections.com/submit-product/ | OK |
| 177 | form | https://www.submit.biz/ | OK |
| 181 | form | https://tap4.ai/cn/submit | OK |
| 204 | form | https://viesearch.com/submit | OK |
| 225 | form | http://www.fwol.cn/infos_add.php | OK |
| 229 | form | https://tigg.cc/share | OK |
| 231 | form | https://www.yjpoo.com/submit-ai-tool/ | OK |
| 232 | form | https://www.aiheron.com/promote | OK |
| 234 | form | https://www.hhlink.com/%e6%8f%90%e4%ba%a4%e6%96%b0%e7%bd%91%e7%ab%99 | OK |
| 240 | form | https://lbbai.com/contribute | OK |
| 241 | pending | https://aimojo.pro/submit/ | OK |
| 260 | pending | https://info-listings.com/submit.php | OK |
| 269 | pending | https://www.sitelike.org/add-site | OK |
| 273 | pending | https://www.thetoolbus.ai/submit-tools | OK |
| 286 | pending | https://dang.ai/ | OK |
| 337 | profile | https://forum.gekko.wizb.it/user-14910.html | OK |
| 340 | profile | https://calaos.fr/forum/member.php?action=profile&uid=7732 | OK |
| 1037 | search_engine | https://www.activesearchresults.com/addwebsite.php | OK |

## 🔍 保留 NULL (待复查)

| ID | 类型 | URL | 原因 |
|----|------|-----|------|
| 20 | directory | https://tally.so/r/2ekv4g?ref=boostmytool.com | No forms found on page |
| 22 | directory | https://betalist.com/dashboard | 1 form(s) found, none with URL field |
| 24 | directory | https://www.aixploria.com/en/submit-ai-tool-or-feature-company/#submit | No forms found on page |
| 26 | directory | https://topai.tools/submit | No forms found on page |
| 30 | directory | https://stackviv.ai/submit | No forms found on page |
| 31 | directory | https://productivity.directory/s/submit | No forms found on page |
| 33 | directory | https://opentools.ai/friends/launch-tool | No forms found on page |
| 36 | directory | https://findmyaitool.com/submit-tool | No forms found on page |
| 37 | directory | https://eliteai.tools/tool/submit-new-tool?tab=launch | 1 form(s) found, none with URL field |
| 38 | directory | https://easywithai.com/submit-tool/ | Page timeout |
| 39 | directory | https://bowora.com/dashboard/startups | 1 form(s) found, none with URL field |
| 43 | directory | https://aitoptools.com/account/submit-tool/ | 2 form(s) found, none with URL field |
| 45 | directory | https://aidirectory.wiki/submit-tool | No forms found on page |
| 47 | directory | https://aicenter.ai/submit-tools | No forms found on page |
| 65 | form | https://www.fsl123.com/contribute | Page timeout |
| 66 | form | https://www.247webdirectory.com/ | No forms found on page |
| 67 | form | https://2agi.net/zh/submit | Page.goto: net::ERR_CERT_DATE_INVALID at https://2agi.net/zh/submit
Call log:
   |
| 72 | form | http://www.alistdirectory.com/submit.php | Page timeout |
| 74 | form | https://www.abc-directory.com/submiturl | No forms found on page |
| 76 | form | https://ai-finder.net/ | Page timeout |
| 77 | form | https://aihomes.io/submit/submit-tool | No forms found on page |
| 78 | form | https://library.phygital.plus/tool-submission | No forms found on page |
| 79 | form | https://www.ainavpro.com/contribute | Page.goto: net::ERR_CERT_DATE_INVALID at https://www.ainavpro.com/contribute
Cal |
| 82 | form | https://aitoolsup.com/submit-tool/ | Page timeout |
| 86 | form | https://aigclist.com/submit-ai-tools-free/ | 1 form(s) found, none with URL field |
| 87 | form | https://www.aigc.cn/submit | No forms found on page |
| 88 | form | https://ailib.ru/en/add-ai/ | 1 form(s) found, none with URL field |
| 89 | form | https://ailibri.com/addai | No forms found on page |
| 90 | form | https://aitoolguru.com/ | Page timeout |
| 91 | form | https://aitoolmall.com/submit/ | No forms found on page |
| 92 | form | https://aitoolsdirectory.com/submit-tool | Page timeout |
| 93 | form | https://aiwikitools.com/submit-a-tool/ | 1 form(s) found, none with URL field |
| 94 | form | https://www.aidashi.cn/sl | Page.goto: net::ERR_CERT_COMMON_NAME_INVALID at https://www.aidashi.cn/sl
Call l |
| 95 | form | https://ai.94kan.cn/submit | Page.goto: net::ERR_CERT_AUTHORITY_INVALID at https://ai.94kan.cn/submit
Call lo |
| 96 | form | https://jinshuju.net/f/bhefyj | No forms found on page |
| 97 | form | https://www.ailookme.com/%e7%bd%91%e5%9d%80%e6%8f%90%e4%ba%a4 | No forms found on page |
| 98 | form | https://www.aitool123.cc/%e6%8f%90%e4%ba%a4%e6%94%b6%e5%bd%95/ | Connection refused/closed |
| 101 | form | https://aibusinesstool.com/ | No forms found on page |
| 103 | form | https://www.aisupersmart.com/submit-tool/ | eval failed: Page.evaluate: Execution context was destroyed, most likely because of a navigat |
| 104 | form | https://www.allbusinessdirectory.biz/directory.php?page=submission-guidelines | No forms found on page |
| 105 | form | http://www.allstartups.info/startups/submit | Page.goto: net::ERR_CERT_DATE_INVALID at http://www.allstartups.info/startups/su |
| 108 | form | https://alternative.me/how-to/submit-software/ | No forms found on page |
| 109 | form | https://apprater.net/add/ | Page timeout |
| 110 | form | http://appiod.com/submit-app-for-review/ | No forms found on page |
| 111 | form | https://landing.mycloudmedia.co.uk/apps-and-websites-submit-ai-or-saas-tool/new-submission.html | 1 form(s) found, none with URL field |
| 112 | form | https://appsthunder.com/submit-your-app/ | No forms found on page |
| 114 | form | https://www.businessseek.biz/page.php?page=submission-policy | eval failed: Page.evaluate: TypeError: (form.action // "").slice is not a function
    at eva |
| 117 | form | https://www.cipinet.com/submit.php | Page timeout |
| 119 | form | https://datatau.net/ | Page timeout |
| 123 | form | https://draeno.io/submit-a-tool/ | No forms found on page |
| 124 | form | https://www.dropyourai.com/submit-tool | No forms found on page |
| 125 | form | https://fuun.fun/talk.html | No forms found on page |
| 126 | form | https://fiddy.co/ | Connection refused/closed |
| 127 | form | https://foundr.ai/ | 2 form(s) found, none with URL field |
| 128 | form | https://freeaitool.ai/submit | No forms found on page |
| 129 | form | https://free-ai-tools-directory.com/submit-request/ | Page timeout |
| 130 | form | https://www.directory-free.com/submit/submit.php | 3 form(s) found, none with URL field |
| 131 | form | https://www.freeinternetwebdirectory.com/submit.php | No forms found on page |
| 134 | form | https://fundamaker.com/ | Page body empty or inaccessible |
| 135 | form | https://www.futureagitools.com/submit-a-site | No forms found on page |
| 136 | form | https://www.futuretools.io/submit-a-tool | Captcha required |
| 137 | form | https://gainweb.org/ | 1 form(s) found, none with URL field |
| 141 | form | https://www.humanornot.co/submit-tool | Page timeout |
| 142 | form | https://indietools.co/ | Page body empty or inaccessible |
| 144 | form | https://www.interestedinai.com/submit-tool | No forms found on page |
| 146 | form | https://www.joinly.xyz/ | No forms found on page |
| 147 | form | https://www.killerstartups.com/submit-startup/ | No forms found on page |
| 148 | form | https://launched.io/ | Page.goto: net::ERR_CERT_DATE_INVALID at https://launched.io/
Call log:
  - navi |
| 153 | form | https://nextgentools.me/submit-your-tool | 1 form(s) found, none with URL field |
| 154 | form | https://www.nextool.ai/submit-a-tool | No forms found on page |
| 157 | form | https://paxi.ai/submit | No forms found on page |
| 158 | form | https://pitchwall.co/ | No forms found on page |
| 160 | form | https://primeindies.com/ | eval failed: Page.evaluate: Execution context was destroyed, most likely because of a navigat |
| 162 | form | https://www.promotebusinessdirectory.com/submit.php | Cloudflare challenge on page |
| 165 | form | https://simplelister.com/ | No forms found on page |
| 167 | form | https://www.siteswebdirectory.com/submit.php | 1 form(s) found, none with URL field |
| 168 | form | https://solo.xin/product | No forms found on page |
| 171 | form | https://www.spottheai.com/submit | Page body empty or inaccessible |
| 174 | form | https://startupbase.io/ | No forms found on page |
| 175 | form | https://www.startupranking.com/ | No forms found on page |
| 176 | form | https://www.submissionwebdirectory.com/ | No forms found on page |
| 178 | form | https://www.superaitools.io/submit-a-tool | No forms found on page |
| 179 | form | https://supertools.therundown.ai/submit | 2 form(s) found, none with URL field |
| 180 | form | https://www.txtlinks.com/sug_url.php?cat_id=0 | 1 form(s) found, none with URL field |
| 182 | form | http://techfaster.com/submit-your-company/ | No forms found on page |
| 183 | form | https://www.techpluto.com/submit-a-startup/ | 3 form(s) found, none with URL field |
| 184 | form | https://thalesdirectory.com/submit/ | No forms found on page |
| 186 | form | https://thestartuppitch.com/post-a-pitch/ | Page.goto: net::ERR_CERT_COMMON_NAME_INVALID at https://thestartuppitch.com/post |
| 187 | form | https://www.toolhunter.ai/submit-a-tool | No forms found on page |
| 188 | form | https://toolscout.ai/submit | No forms found on page |
| 189 | form | https://toolsstory.net/add-listing/ | No forms found on page |
| 190 | form | https://form.typeform.com/to/lqctjr | Page timeout |
| 191 | form | https://toolsai.net/add-listing/ | Page.goto: net::ERR_CERT_DATE_INVALID at https://toolsai.net/add-listing/
Call l |
| 193 | form | https://toools.design/ | 1 form(s) found, none with URL field |
| 194 | form | https://www.topbestalternatives.com/ | 1 form(s) found, none with URL field |
| 195 | form | https://topapps.ai/submit | No forms found on page |
| 196 | form | https://trackbes.com/submit-tool | Page body empty or inaccessible |
| 197 | form | https://www.tsection.com/ | 1 form(s) found, none with URL field |
| 201 | form | https://www.uneed.best/promote-your-tool | No forms found on page |
| 203 | form | https://unmatchedstyle.com/submit | Page timeout |
| 206 | form | https://www.wewaat.com/submitnewtool | No forms found on page |
| 207 | form | https://www.whatlaunched.today | Cloudflare challenge on page |
| 209 | form | https://tally.so/r/wkekz1 | No forms found on page |
| 210 | form | https://www.aitoolhunt.com/ | No forms found on page |
| 211 | form | https://aitoolslist.io/submit-ai-tool/ | No forms found on page |
| 212 | form | https://aiwith.me/zh/submit | No forms found on page |
| 213 | form | https://bigstartups.co/overview/list-product | No forms found on page |
| 215 | form | https://www.findcool.tools/submit-tool | No forms found on page |
| 216 | form | https://iforai.com/submit_website/ | eval failed: Page.evaluate: TypeError: (form.action // "").slice is not a function
    at eva |
| 217 | form | https://www.insanelycooltools.com/submit | Page body empty or inaccessible |
| 218 | form | https://once.tools/ | No forms found on page |
| 219 | form | https://osalt.com/suggest | Page timeout |
| 220 | form | https://www.techdirectory.io/get-listed | No forms found on page |
| 221 | form | https://www.tools-ai.online/tool-submit | Captcha required |
| 222 | form | https://zhexieai.com/%e6%8f%90%e4%ba%a4%e7%bd%91%e5%9d%80 | Page timeout |
| 223 | form | https://ywyj.cn/ | Page timeout |
| 224 | form | https://nancheng.fun/contribute | Connection refused/closed |
| 226 | form | https://wechalet.cn/appstore/add | No forms found on page |
| 227 | form | http://toolsdar.mikecrm.com/nix44in | No forms found on page |
| 228 | form | https://www.dongaiapp.com/sub | Connection refused/closed |
| 230 | form | https://xinquji.com/ | No forms found on page |
| 235 | form | https://www.deepdhai.com/submit | 1 form(s) found, none with URL field |
| 237 | form | https://www.zhifoubox.com/submission | Page.goto: net::ERR_HTTP2_PROTOCOL_ERROR at https://www.zhifoubox.com/submission |
| 238 | form | https://dizkaz.com/ | No forms found on page |
| 239 | form | https://xquan.net/help?tab=submit-guide | No forms found on page |
| 242 | pending | https://ainews.guru/ai-app-submission/ | No forms found on page |
| 243 | pending | https://aiscout.net/ | No forms found on page |
| 244 | pending | https://aiworthy.org/submit-tool/ | No forms found on page |
| 245 | pending | https://www.aihub.cn/write | 3 form(s) found, none with URL field |
| 246 | pending | https://www.h1z1tmc.com/submit | Page.goto: net::ERR_CERT_DATE_INVALID at https://www.h1z1tmc.com/submit
Call log |
| 247 | pending | https://www.51aiyz.com/about | No forms found on page |
| 248 | pending | https://www.addictivetips.com/tip-us/ | No forms found on page |
| 249 | pending | https://www.affordhunt.com/onesubmitai | No forms found on page |
| 250 | pending | https://aipediahub.com/submit/ | No forms found on page |
| 251 | pending | https://aitime.space/submit | No forms found on page |
| 252 | pending | https://www.aitoolkit.org/submit | No forms found on page |
| 254 | pending | https://designtools.ai/submit/ | No forms found on page |
| 255 | pending | https://www.designrush.com/submit/agency | 1 form(s) found, none with URL field |
| 257 | pending | https://www.futurepedia.io/basic | No forms found on page |
| 258 | pending | https://www.gooddesign.tools/submit | No forms found on page |
| 259 | pending | https://www.itjuzi.com/addcompany | No forms found on page |
| 261 | pending | https://www.lovejay.top/%e7%bd%91%e7%ab%99%e6%8a%95%e7%a8%bf | No forms found on page |
| 262 | pending | https://www.launchingnext.com/submit/ | No forms found on page |
| 263 | pending | https://www.libhunt.com/repo/submit | No forms found on page |
| 264 | pending | https://aitools.neilpatel.com/submit/ | No forms found on page |
| 265 | pending | https://nocodefamily.com/submit-tool | No forms found on page |
| 266 | form | https://airtable.com/appcn6nvv5iyo3x/pagzzygl6fei2rwdq/form | No forms found on page |
| 267 | pending | https://payonceapps.com/add-your-app/ | No forms found on page |
| 268 | pending | https://seofai.com/submit-tool/ | No forms found on page |
| 270 | pending | https://www.spotsaas.com/get-listed | No forms found on page |
| 271 | pending | https://startupstash.com/add-listing/ | Page timeout |
| 272 | pending | https://www.stork.ai/ | No forms found on page |
| 274 | pending | https://toolfinder.co/submit-your-tool | No forms found on page |
| 275 | pending | https://www.toolbase.ai/toolbase/submit-tool | No forms found on page |
| 276 | pending | https://top10.now/submit | No forms found on page |
| 277 | pending | https://vteam.ai/submit-tool | No forms found on page |
| 278 | pending | https://www.webwiki.com/info/add-website.html | No forms found on page |
| 279 | pending | https://youraitool.com/submit-tool | No forms found on page |
| 280 | pending | https://chatgptdemo.com/submit-new-ai-tool/ | 1 form(s) found, none with URL field |
| 281 | pending | https://fastpedia.io/submit-tool/ | No forms found on page |
| 283 | pending | https://17yongai.com/submit-website | Page timeout |
| 284 | pending | https://leiydz.com/contribute | No forms found on page |
| 285 | pending | https://aoh.cc/contribute | No forms found on page |
| 287 | form | https://aitoptools.com/login?redirect_to=submit | 2 form(s) found, none with URL field |
| 288 | form | https://alternativeto.net/faq/ | No forms found on page |
| 290 | form | https://betalist.com/users/sign_in | No forms found on page |
| 291 | form | https://broadwise.org/t/how-to-promote-your-startup-on-broadwise-org/125 | No forms found on page |
| 292 | listing | https://devhunt.org/ | No forms found on page |
| 293 | article | https://hackernoon.com/ | Page timeout |
| 294 | article | https://hashnode.com/discussions | no submission form or URL field detected |
| 295 | listing | https://hellogithub.com/ | No forms found on page |
| 296 | listing | https://www.indiehackers.com/products | No forms found on page |
| 297 | form | https://makerpeak.com/sign-up?redirect=/profile/products/submit | Page timeout |
| 298 | listing | https://www.producthunt.com/ | No forms found on page |
| 299 | article | https://news.ycombinator.com/submit | Page timeout |
| 300 | article | https://www.v2ex.com/go/create | Page timeout |
| 301 | article | https://w2solo.com/topics/newproduct | no submission form or URL field detected |
| 302 | article | https://dev.to/ | no submission form or URL field detected |
| 303 | article | https://www.reddit.com/r/alphaandbetausers/ | Page timeout |
| 304 | article | https://reddit.com/r/entrepreneur | Page timeout |
| 305 | article | https://www.reddit.com/r/imadethis/ | Page.goto: net::ERR_CONNECTION_RESET at https://www.reddit.com/r/imadethis/
Call |
| 306 | article | https://www.reddit.com/r/internetisbeautiful/ | Page timeout |
| 307 | article | https://reddit.com/r/sideproject | Page timeout |
| 308 | article | https://reddit.com/r/startups | Page timeout |
| 309 | article | https://www.reddit.com/r/buildinpublic/ | Page.goto: net::ERR_CONNECTION_RESET at https://www.reddit.com/r/buildinpublic/
 |
| 310 | article | https://www.reddit.com/r/opensource/ | Page timeout |
| 311 | article | https://www.reddit.com/r/selfhosted/ | Page.goto: net::ERR_CONNECTION_RESET at https://www.reddit.com/r/selfhosted/
Cal |
| 312 | article | https://www.reddit.com/r/webdev/ | Page timeout |
| 314 | article | https://web.okjike.com/ | no submission form or URL field detected |
| 315 | article | https://juejin.cn/ | no submission form or URL field detected |
| 331 | profile | https://multichain.com/qa/user/parrotcatsup3 | Forum profile page - needs login to edit |
| 332 | profile | https://forums.maxperformanceinc.com/forums/member.php?u=202517 | Forum profile page - needs login to edit |
| 333 | profile | https://www.majalahsains.com/careers/employer/lawrence/ | Page timeout |
| 334 | profile | https://labsk.net/index.php?action=profile%3bu%3d50620 | Page timeout |
| 335 | profile | https://forum.epicbrowser.com/profile.php?id=78821 | Page timeout |
| 336 | profile | http://blog.setlist.fm/2009/03/setlistfm-hits-blogosphere.html | Page timeout |
| 338 | profile | https://www.blafusel.de/phpbb/memberlist.php?mode=viewprofile&u=8625 | Forum profile page - needs login to edit |
| 339 | profile | https://www.makeupsavvy.co.uk/2019/12/best-budget-concealers-for-pale-skin-2019.html | Page timeout |
| 341 | profile | https://blog.tallmenshoes.com/2018/10/5-ways-to-elevate-your-fashion.html | Page timeout |
| 342 | profile | https://www.predictiveanalyticsworld.com/machinelearningtimes/dont-let-yourself-be-fooled-by-data-drift/13125/ | Page timeout |
| 343 | profile | https://www.weirdsciencedccomics.com/2022/02/batmancatwoman-10-review.html | Connection refused/closed |
| 344 | profile | https://www.itsfilmedthere.com/2019/01/whats-happening.html | Page timeout |
| 345 | profile | https://www.negociosyemprendimiento.org/2024/12/historia-temu.html?m=0 | Page timeout |
| 346 | profile | https://www.cornbeanspigskids.com/2024/08/back-to-school-my-kids-favorite.html | Page timeout |
| 347 | profile | https://www.techqiah.com/2024/11/192-168-100-1.html | Page timeout |
| 348 | profile | https://iotwreport.com/letitia-james-indicted-for-banking-fraud/ | No URL field or editable form found |
| 349 | profile | http://www.eilentein.com/2019/02/ryijy-ja-kuinka-sen-tein.html | Page timeout |
| 350 | profile | http://www.thinkgrowgiggle.com/2020/07/10-best-mentor-texts-to-use-for-reading.html | Page timeout |
| 392 | blog_comment | https://sharonsantoni.com/2023/05/making-strawberry-jam-2/ | Page timeout |
| 393 | blog_comment | https://www.visitrichmond.co.uk/blog/read/2024/03/english-tourism-week-2024-gardens-and-parks-b48 | Page timeout |
| 399 | blog_comment | https://www.ginjfo.com/actualites/logiciels/jeux-video-logiciels/les-sims-4-fetent-leur-25e-anniversaire-avec-du-nouveau-contenu-massif-20250227 | No comment form in DOM |
| 404 | blog_comment | https://blog.pianetamamma.it/amoredimamma/polpette-di-prosciutto-cotto-e-ricotta-al-forno/ | Captcha required |
| 406 | blog_comment | https://www.yourcupofcake.com/banana-bread-coffee-cake/ | No comment form in DOM |
| 407 | blog_comment | https://lovestrategies.com/are-you-a-walking-red-flag-7-habits-that-might-be-sabotaging-your-love-life/ | Page timeout |
| 422 | blog_comment | https://joaniesimon.com/94f737822923f4567e1a7ce9681e5b9a-2/ | No comment form in DOM |
| 436 | blog_comment | https://jonnegroni.com/2017/11/20/cinemaholics-review-justice-league-punisher/ | Page timeout |
| 443 | blog_comment | http://www.kt.rim.or.jp/~youie/cgi-bin/nanmeri/nanmeri.cgi?mode=comment&no=239 | Comment form exists but no comment textarea |
| 448 | blog_comment | http://www.superstore.co.jp/wp-includes/fonts/diary.cgi?mode=comment&no=116 | Page timeout |
| 449 | blog_comment | https://www.mae.gov.bi/en/an-audience-with-the-iom-head-of-the-mission-in-burundi/ | Captcha required |
| 452 | blog_comment | http://www.kcn.ne.jp/~gorosan/cgi-bin/diarypro/diary.cgi?mode=comment&no=97 | No comment form in DOM |
| 454 | blog_comment | https://ride.guru/content/newsroom/finding-your-fare-with-rideguru-a-how-to-guide | Page timeout |
| 455 | blog_comment | https://cantstayoutofthekitchen.com/2022/01/06/blueberry-walnut-overnight-oatmeal/ | No comment form in DOM |
| 460 | blog_comment | https://www.speechandlanguagekids.com/week-7-summer-speech-challenge/ | No comment form in DOM |
| 471 | blog_comment | https://www.yourcupofcake.com/easy-to-make-snowman-cupcakes/ | No comment form in DOM |
| 475 | blog_comment | https://loveandmarriageblog.com/beach-water-cocktail/ | No comment form in DOM |
| 484 | blog_comment | https://everythingboardgames.com/2024/11/exploring-the-world-of-online-board-games.html | No comment form in DOM |
| 486 | blog_comment | https://www.moonsoap.com/hpgen/hpb/entries/8.html | No comment form in DOM |
| 491 | blog_comment | https://www.yourcupofcake.com/almond-banana-bread/ | No comment form in DOM |
| 497 | blog_comment | https://squatuniversity.com/2015/12/01/the-squat-fix-hip-mobility-pt-1/comment-page-2/ | Page timeout |
| 500 | blog_comment | https://www.mangoandsalt.com/2023/05/04/galgos-podencos-tout-savoir-adoption-levriers-despagne/ | Page timeout |
| 505 | blog_comment | https://www.patisserie-okumoto.com/hpgen/hpb/entries/1.html?https%3a%2f%2ffuhrerschein-eu.com%2f= | No comment form in DOM |
| 506 | blog_comment | https://squatuniversity.com/2016/04/07/how-to-perfect-the-front-squat/comment-page-4/ | Page timeout |
